############################################################
# Dockerfile to run a Django-based web application
# Based on an AMI
############################################################
# Set the base image to use to Ubuntu
FROM 017357459259.dkr.ecr.ap-south-1.amazonaws.com/gia-dev:golambdalatest
#FROM golambda_image_golambda_2

RUN adduser 1000



#RUN chown  1000 /code/*
#RUN chown  1000 /docker-entrypoint.sh
COPY . /usr/local/goibibo/source/diana_lambda/vertical/
EXPOSE 80

#RUN ["chmod", "+x", "/docker-entrypoint.sh"]
CMD ["/usr/bin/supervisord", "-n"]
