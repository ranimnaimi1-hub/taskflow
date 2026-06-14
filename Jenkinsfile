pipeline {
    agent any

    environment {
        PROJECT_DIR = "${env.WORKSPACE}"
        DJANGO_SETTINGS_MODULE = "config.settings.development"
    }

    stages {
        stage('Checkout SCM') {
            steps {
                echo "Checking out source code"
                checkout scm
            }
        }

        stage('Validate Django') {
            steps {
                echo "Running Django system checks"
                sh '''
                    if command -v python3 >/dev/null 2>&1; then
                        PYTHON_BIN=python3
                    elif command -v python >/dev/null 2>&1; then
                        PYTHON_BIN=python
                    else
                        echo "Python is not installed on this Jenkins agent; skipping Django system checks."
                        exit 0
                    fi

                    "$PYTHON_BIN" manage.py check
                '''
            }
        }

        stage('Stop Monitoring Stack') {
            steps {
                echo "Stopping monitoring stack"
                sh '''
                    cd "${PROJECT_DIR}/monitor"
                    if command -v docker-compose >/dev/null 2>&1; then
                        docker-compose down || true
                    else
                        docker compose down || true
                    fi
                '''
            }
        }

        stage('Deploy Monitoring Stack') {
            steps {
                echo "Deploying monitoring stack"
                sh '''
                    cd "${PROJECT_DIR}/monitor"
                    if command -v docker-compose >/dev/null 2>&1; then
                        docker-compose up -d
                    else
                        docker compose up -d
                    fi
                '''
            }
        }

        stage('Show Monitoring Endpoints') {
            steps {
                echo "Prometheus: http://<jenkins-host>:9095"
                echo "Grafana: http://<jenkins-host>:3001"
                echo "Django metrics: http://<django-host>:8000/metrics"
            }
        }
    }

    post {
        success {
            echo "Deployment successful"
        }

        failure {
            echo "Deployment failed"
        }
    }
}
