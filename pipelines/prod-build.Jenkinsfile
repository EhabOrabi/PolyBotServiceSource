pipeline {
    agent {
        label 'general'
    }

    triggers {
        githubPush()
    }

    options {
        timeout(time: 10, unit: 'MINUTES')  // discard the build after 10 minutes of running
        timestamps()  // display timestamp in console output
    }

    environment {
        IMAGE_TAG = "v1.0.$BUILD_NUMBER"
        IMAGE_BASE_NAME = "polybot2_prod"

        // Update this line with the correct credential ID
        DOCKER_CREDS = credentials('3fae05e6-df33-4107-8ea2-72928aac9e90')
        DOCKER_USERNAME = "${DOCKER_CREDS_USR}"  // The _USR suffix added to access the username value
        DOCKER_PASS = "${DOCKER_CREDS_PSW}"      // The _PSW suffix added to access the password value
    }

    stages {
        stage('Docker setup') {
            steps {
                sh '''
                  echo "Logging into Docker Hub with username: $DOCKER_CREDS_USR"
                  docker login -u $DOCKER_CREDS_USR -p $DOCKER_CREDS_PSW || echo "Docker login failed"
                '''
            }
        }

        stage('Build app container') {
            steps {
                sh '''
                    IMAGE_FULL_NAME=$DOCKER_USERNAME/$IMAGE_BASE_NAME:$IMAGE_TAG
                    docker build -t $IMAGE_FULL_NAME .
                    docker push $IMAGE_FULL_NAME
                '''
            }
        }

        stage('Trigger Deploy') {
            steps {
                build job: 'polybotDeployProd', wait: false, parameters: [
                    string(name: 'SERVICE_NAME', value: "prod"),
                    string(name: 'IMAGE_FULL_NAME_PARAM', value: "$DOCKER_USERNAME/$IMAGE_BASE_NAME:$IMAGE_TAG")
                ]
            }
        }
    }
}
