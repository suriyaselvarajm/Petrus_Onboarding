pipeline {
    agent any

    environment {
        SONAR_SCANNER = tool 'SonarScanner'
    }

    stages {

        stage('Clone Code') {
            steps {
                echo 'Pulling source code from GitHub'
                git branch: 'main',
                credentialsId: 'github-ssh',
                url: 'git@github.com:suriyaselvarajm/Petrus_Onboarding.git'
            }
        }

        stage('Install Dependencies') {
            steps {
                sh '''
                python3 -m venv venv
                . venv/bin/activate
                pip install -r requirements.txt
                '''
            }
        }

        stage('Run Tests') {
            steps {
                sh '''
                . venv/bin/activate
                pytest --cov=. --cov-report=xml
                '''
            }
        }

        stage('SonarQube Analysis') {
            steps {
                withSonarQubeEnv('SonarQube') {
                    sh '''
                    . venv/bin/activate

                    $SONAR_SCANNER/bin/sonar-scanner \
                    -Dsonar.projectKey=Petrus_Onboarding \
                    -Dsonar.sources=. \
                    -Dsonar.python.coverage.reportPaths=coverage.xml
                    '''
                }
            }
        }

        stage('Build Docker Image') {
            steps {
                sh '''
                docker build -t petrus-onboarding .
                '''
            }
        }

        stage('Deploy') {
            steps {
                sh '''
                docker stop petrus-app || true
                docker rm petrus-app || true

                docker run -d \
                --name petrus-app \
                -p 5000:5000 \
                petrus-onboarding
                '''
            }
        }
    }

    post {
        success {
            echo 'Pipeline completed successfully'
        }

        failure {
            echo 'Pipeline failed'
        }
    }
}
