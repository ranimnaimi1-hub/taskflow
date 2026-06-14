pipeline {
    agent any

    stages {

        stage('Checkout SCM') {
            steps {
                echo "📥 Checking out source code...."
                checkout scm
            }
        }

        stage('Stop Monitoring Stack') {
            steps {
                echo "🛑 Stopping monitoring stack..."
                sh '''
                    cd /workspace/taskflow/taskflow_backend_django/monitor \
                    && docker compose down || true
                '''
            }
        }

        stage('Deploy Monitoring Stack') {
            steps {
                echo "📊 Deploying monitoring stack..."
                sh '''
                    cd /workspace/taskflow/taskflow_backend_django/monitor \
                    && docker compose up -d
                '''
            }
        }

    }

    post {
        success {
            echo "✅ Deployment successful"
        }

        failure {
            echo "❌ Deployment failed"
        }
    }
}