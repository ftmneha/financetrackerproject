
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
                    python -m pip install --upgrade pip --timeout 120 --retries 5
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
                        --format=columns
                '''
            }
        }

        stage('Secret Detection - Gitleaks') {
            steps {
                sh '''
                    set -eu

                    GITLEAKS_VERSION=8.30.1
                    TEMP_DIR=$(mktemp -d)
                    trap 'rm -rf "$TEMP_DIR"' EXIT

                    curl -fsSL \
                        "https://github.com/gitleaks/gitleaks/releases/download/v${GITLEAKS_VERSION}/gitleaks_${GITLEAKS_VERSION}_linux_x64.tar.gz" \
                        -o "$TEMP_DIR/gitleaks.tar.gz"

                    tar -xzf "$TEMP_DIR/gitleaks.tar.gz" \
                        -C "$TEMP_DIR" gitleaks

                    "$TEMP_DIR/gitleaks" version

                    "$TEMP_DIR/gitleaks" git \
                        --redact \
                        --no-banner \
                        --report-format json \
                        --report-path reports/gitleaks-report.json \
                        .
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
