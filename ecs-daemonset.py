#!/usr/bin/env python3

# https://aws.amazon.com/blogs/compute/how-to-create-a-custom-scheduler-for-amazon-ecs/

from datetime import datetime, timezone
import boto3
import argparse
import logging
import pprint
import sys
import os
import time

# Set up logger
logging.getLogger(__name__)
pp = pprint.PrettyPrinter(indent=4)

# Set up boto client
ecs = boto3.client('ecs')

def listServices(clusterName):
    response = ecs.list_services(cluster=clusterName)
    serviceArns = response['serviceArns']
    while response.get('nextToken', None) is not None:
        response = ecs.list_services(
            cluster=clusterName,
            nextToken=response['nextToken']
        )
        serviceArns.extend(response['serviceArns'])

    return serviceArns


def describeServices(clusterName, serviceArns):

    instance_count = len(getInstanceArns(clusterName))

    for serviceArn in serviceArns:
        logging.debug("Evaluating service ARN: {}".format(serviceArn))

        service_response = ecs.describe_services(
            cluster=clusterName, services=[serviceArn]
        )
        task_definition = service_response['services'][0]['taskDefinition']
        desired_count = service_response['services'][0]['desiredCount']
        placement_constraints = service_response['services'][0]['placementConstraints']

        # if `desired_count` is 0, consider it disabled
        if desired_count == 0:
            logging.debug("Service {} is disabled.".format(serviceArn))
            continue

        # we only consider services with 'distinctInstance' placement
        if len(placement_constraints) and 'distinctInstance' not in [v['type'] for v in placement_constraints]:
            logging.debug("Service {} is not configured with distinctInstance placement.".format(serviceArn))
            continue

        # don't scale if we don't need to
        if desired_count == instance_count:
            logging.debug("Service {} already has correct desired count.".format(serviceArn))
            continue

        # check task for ECS_DAEMONSET label
        task_definition_response = ecs.describe_task_definition(
            taskDefinition=task_definition
        )
       
        if 'ECS_DAEMONSET' in list(task_definition_response['taskDefinition']['containerDefinitions'][0]['dockerLabels']):
            logging.info("Service {} has {} desired tasks, but should be {}.".format(serviceArn, desired_count, instance_count))
            ecs.update_service(
                cluster=clusterName,
                service=serviceArn,
                desiredCount=instance_count
            )
            
def getInstanceArns(clusterName):
    # Get instances in the cluster
    response = ecs.list_container_instances(cluster=clusterName, status='ACTIVE')
    containerInstancesArns = response['containerInstanceArns']
    # If there are more instances, keep retrieving them
    while response.get('nextToken', None) is not None:
        response = ecs.list_container_instances(
            cluster=clusterName,
            status='ACTIVE',
            nextToken=response['nextToken']
        )
        containerInstancesArns.extend(response['containerInstanceArns'])

    return containerInstancesArns


def main():
    parser = argparse.ArgumentParser(
        description='ECS "scheduler" that places services on each node in the cluster.'
    )
    parser.add_argument(
        '-c', '--cluster',
        default='default',
        help='The short name or full Amazon Resource Name (ARN) of your ECS cluster. If you do not specify a cluster, the default cluster is assumed.'
    )
    parser.add_argument(
        '-l', '--log-level',
        default='info',
        help='Log level.'
    )
    args = parser.parse_args()

    logging.basicConfig(format='%(asctime)s - %(levelname)s: %(message)s',
                        datefmt='%m/%d/%Y %I:%M:%S %p', level=logging.getLevelName(args.log_level.upper()))

    sleep = os.getenv('RESOURCE_CHECK_INTERVAL', 60)
    while True:
        serviceArns = listServices(args.cluster)
        describeServices(args.cluster, serviceArns)
        logging.debug("Sleeping for {}s...".format(sleep))
        time.sleep(int(sleep))


if __name__ == "__main__":
    main()
