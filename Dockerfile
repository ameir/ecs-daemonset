FROM python:3-alpine

ARG APP_NAME=ecs-daemonset
ARG DIR=/opt/$APP_NAME
ARG RUN_USER=$APP_NAME
ENV APP_NAME=$APP_NAME

RUN mkdir -vp $DIR
WORKDIR $DIR
COPY *.sh *.py ./
RUN ./build.sh
USER $RUN_USER

CMD ["./run.sh"]
