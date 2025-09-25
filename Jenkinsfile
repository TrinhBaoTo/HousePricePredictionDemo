pipeline {
    agent any

    environment {
        APP_NAME   = 'house-price-flask'
        IMAGE_NAME = "house-price-flask"
        IMAGE_TAG  = "${env.BUILD_NUMBER}"
    }

    stages {
        stage('Checkout') {
            steps {
                checkout scm
                sh 'git rev-parse --short HEAD > GIT_SHA.txt'
            }
            post {
                success {
                archiveArtifacts artifacts: 'GIT_SHA.txt', fingerprint: true
                }
            }
        }

        stage('Build') {
            steps {
                sh '''
                echo "Building Docker image..."
                docker build -t ${IMAGE_NAME}:${IMAGE_TAG} -t ${IMAGE_NAME}:latest .
                docker image inspect ${IMAGE_NAME}:${IMAGE_TAG} --format='{{.Id}}' > IMAGE_ID.txt
                '''
            }
            post {
                success {
                    archiveArtifacts artifacts: 'IMAGE_ID.txt', fingerprint: true
                }
            }
            }
        }
        stage('Install Dependencies') {
            steps {
                sh 'npm install'
            }
        }
         stage('Run Tests') {
             steps {
                sh 'npm test || true' 
             }
         }
         stage('Generate Coverage Report') {
             steps {
                 sh 'npm run coverage || true'
             }
         }
        stage('NPM Audit (Security Scan)') {
             steps {
                sh 'npm audit || true'
             }
        }
        stage('SonarCloud Analysis') {
            steps {
                withSonarQubeEnv('HousePricePredictionDemo') {
                sh 'npm run coverage || true'  
                sh 'sonar-scanner'          
                }
            }
            }
            stage('Quality Gate') {
            steps {
                timeout(time: 2, unit: 'MINUTES') {
                waitForQualityGate abortPipeline: true
                }
            }
        }
    }
}