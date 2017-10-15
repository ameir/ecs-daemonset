# ecs-daemonset

Place specific containers on every instance of your ECS cluster.

ECS is a nice, thin wrapper around Docker, but anyone who's used it long enough in production knows it's a little too thin.

Kubernetes has a notion of a [`DaemonSet`](https://kubernetes.io/docs/concepts/workloads/controllers/daemonset/), which is a essentially a container (or set of containers) that runs on each node of the cluster.

In ECS, that traditional workaround is to use `aws-cli` or another API client to start an ECS task on an instance via userdata.  If that task fails for any reason or is stopped, it will not start back up on its own.  If anything above that line in your userdata script fails, it won't even attempt to start the task.  Of course, there are ways to spruce up the reliability if you have the resources to take a stab at it.  Or, you can use `ecs-daemonset` to handle this for you.

Instead of creating just a task, you will need to create a service for it with a `distinctInstance` placement constraint.  Additionally, in order to know that a task should be treated as a DaemonSet, you will need to add a Docker label of `ECS_DAEMONSET=true`.  The Datadog CloudFormation template shown later below details how this looks.

## Variables to set

|Variable|Description|Default|
|---|---|---|
|`AWS_REGION`|AWS region where ECS cluster resides|`us-east-1`|
|`ECS_CLUSTER_NAME`|Name of ECS cluster to poll|`default`|
|`RESOURCE_CHECK_INTERVAL`|How often to poll ECS cluster (in seconds)|`60`|

## Sample CloudFormation template of ecs-daemonset

Update this as needed, of course.

```
        "EcsDaemonsetIamRole": {
            "Type": "AWS::IAM::Role",
            "Properties": {
                "AssumeRolePolicyDocument": {
                    "Version": "2012-10-17",
                    "Statement": [
                        {
                            "Effect": "Allow",
                            "Principal": {
                                "Service": [
                                    "ecs-tasks.amazonaws.com"
                                ]
                            },
                            "Action": [
                                "sts:AssumeRole"
                            ]
                        }
                    ]
                },
                "Policies": [
                    {
                        "PolicyName": "ClusterInstancePolicy",
                        "PolicyDocument": {
                            "Version": "2012-10-17",
                            "Statement": [
                                {
                                    "Effect": "Allow",
                                    "Action": [
                                        "ecs:List*",
                                        "ecs:Describe*",
                                        "ecs:UpdateService"
                                    ],
                                    "Resource": "*"
                                }
                            ]
                        }
                    }
                ]
            }
        },
        "EcsTaskDefinitionEcsDaemonsetEcsClusterProduction": {
            "Type": "AWS::ECS::TaskDefinition",
            "Properties": {
                "TaskRoleArn": {
                    "Ref": "EcsDaemonsetIamRole"
                },
                "ContainerDefinitions": [
                    {
                        "Name": "ecs-daemonset-ecs-cluster-production",
                        "Image": "ameir/ecs-daemonset:latest",
                        "Cpu": "64",
                        "Memory": "128",
                        "Environment": [
                            {
                                "Name": "AWS_REGION",
                                "Value": "us-east-1"
                            },
                            {
                                "Name": "ECS_CLUSTER_NAME",
                                "Value": {
                                    "Ref": "EcsClusterProductionEcsCluster"
                                }
                            }
                        ],
                        "Essential": "true",
                        "LogConfiguration": {
                            "LogDriver": "awslogs",
                            "Options": {
                                "awslogs-group": {
                                    "Ref": "EcsClusterProductionCloudwatchLogGroup"
                                },
                                "awslogs-region": "us-east-1",
                                "awslogs-stream-prefix": "ecs-daemonset"
                            }
                        }
                    }
                ]
            }
        },
        "EcsDaemonsetEcsServiceEcsClusterProduction": {
            "Type": "AWS::ECS::Service",
            "Properties": {
                "Cluster": {
                    "Ref": "EcsClusterProductionEcsCluster"
                },
                "TaskDefinition": {
                    "Ref": "EcsTaskDefinitionEcsDaemonsetEcsClusterProduction"
                },
                "DesiredCount": 1
            }
        },
```

## Sample CloudFormation template of a DaemonSet service

We'll use Datadog here since that's popular these days.

```
        "datadogIamRole": {
            "Type": "AWS::IAM::Role",
            "Properties": {
                "AssumeRolePolicyDocument": {
                    "Version": "2012-10-17",
                    "Statement": [
                        {
                            "Effect": "Allow",
                            "Principal": {
                                "Service": [
                                    "ecs-tasks.amazonaws.com"
                                ]
                            },
                            "Action": [
                                "sts:AssumeRole"
                            ]
                        }
                    ]
                },
                "Policies": [
                    {
                        "PolicyName": "ClusterInstancePolicy",
                        "PolicyDocument": {
                            "Version": "2012-10-17",
                            "Statement": [
                                {
                                    "Effect": "Allow",
                                    "Action": [
                                        "ecs:RegisterContainerInstance",
                                        "ecs:DeregisterContainerInstance",
                                        "ecs:DiscoverPollEndpoint",
                                        "ecs:Submit*",
                                        "ecs:Poll",
                                        "ecs:StartTask",
                                        "ecs:StartTelemetrySession"
                                    ],
                                    "Resource": "*"
                                }
                            ]
                        }
                    }
                ]
            }
        },
        "datadogTaskDefinition": {
            "Type": "AWS::ECS::TaskDefinition",
            "Properties": {
                "TaskRoleArn": {
                    "Ref": "datadogIamRole"
                },
                "ContainerDefinitions": [
                    {
                        "Name": "datadog",
                        "Image": "datadog/docker-dd-agent:latest",
                        "Cpu": 10,
                        "Memory": 512,
                        "Essential": true,
                        "LogConfiguration": {
                            "LogDriver": "awslogs",
                            "Options": {
                                "awslogs-group": {
                                    "Ref": "EcsClusterProductionCloudwatchLogGroup"
                                },
                                "awslogs-region": "us-east-1",
                                "awslogs-stream-prefix": "docker-dd-agent"
                            }
                        },
                        "MountPoints": [
                            {
                                "ContainerPath": "/var/run/docker.sock",
                                "SourceVolume": "docker_sock"
                            },
                            {
                                "ContainerPath": "/host/sys/fs/cgroup",
                                "SourceVolume": "cgroup",
                                "ReadOnly": true
                            },
                            {
                                "ContainerPath": "/host/proc",
                                "SourceVolume": "proc",
                                "ReadOnly": true
                            }
                        ],
                        "Environment": [
                            {
                                "Name": "API_KEY",
                                "Value": "xxxxx"
                            },
                            {
                                "Name": "SD_BACKEND",
                                "Value": "docker"
                            }
                        ],
                        "DockerLabels": {
                            "ECS_DAEMONSET": true
                        }
                    }
                ],
                "Volumes": [
                    {
                        "Host": {
                            "SourcePath": "/var/run/docker.sock"
                        },
                        "Name": "docker_sock"
                    },
                    {
                        "Host": {
                            "SourcePath": "/proc/"
                        },
                        "Name": "proc"
                    },
                    {
                        "Host": {
                            "SourcePath": "/cgroup/"
                        },
                        "Name": "cgroup"
                    }
                ],
                "Family": "datadog-ecs-cluster-production"
            }
        },
        "DatadogEcsServiceEcsClusterProduction": {
            "Type": "AWS::ECS::Service",
            "Properties": {
                "Cluster": {
                    "Ref": "EcsClusterProductionEcsCluster"
                },
                "TaskDefinition": {
                    "Ref": "datadogTaskDefinition"
                },
                "DesiredCount": 1,
                "PlacementConstraints": [
                    {
                        "Type": "distinctInstance"
                    }
                ],
                "DeploymentConfiguration": {
                    "MaximumPercent": 100,
                    "MinimumHealthyPercent": 0
                }
            }
        },
```        

## Contributions and issues
Nothing special to it; submit a pull request or file a GitHub issue and I'll check it out when I can.
