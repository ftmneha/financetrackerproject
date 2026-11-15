
pipeline {
    agent {
        label 'python'
    }

    options {
        timeout(time: 30, unit: 'MINUTES')
        buildDiscarder(logRotator(numToKeepStr: '10'))
        disableConcurrentBuilds()
    }

    stages {
        stage('Checkout') {
            steps {
                echo 'Checking out Finance Tracker source code'
                checkout scm
                sh 'mkdir -p reports'
            }
        }

        stage('Install Dependencies') {
            steps {
                sh '''
                    python --version
                    python -m venv .venv
                    . .venv/bin/activate
                    python -m pip install -r requirements.txt
                '''
            }
        }

        stage('Code Quality - Flake8') {
            steps {
                sh '''
                    . .venv/bin/activate
                    flake8 app.py config.py models.py \
                        --max-line-length=120 \
                        --count --statistics
                '''
            }
        }

        stage('Unit Tests') {
            steps {
                sh '''
                    . .venv/bin/activate
                    python -m pytest \
                        --junitxml=reports/test-results.xml \
                        --cov=. \
                        --cov-report=xml:reports/coverage.xml \
                        --cov-report=term \
                        tests/
                '''
            }
        }

        stage('Dependency Security Scan') {
            steps {
                sh '''
                    . .venv/bin/activate
                    pip-audit --path .venv/lib/python3.12/site-packages \
                        --format=json \
                        -o reports/pip-audit-report.json
                '''
            }
        }
    }

    post {
        always {
            echo 'Archiving test results and security reports'
            archiveArtifacts artifacts: 'reports/**',
                allowEmptyArchive: true

            junit testResults: 'reports/test-results.xml',
                allowEmptyResults: true
        }

        success {
            echo 'Finance Tracker CI checks completed successfully!'
        }

        failure {
            echo 'CI pipeline failed. Review the Jenkins console output.'
        }
    }
}
