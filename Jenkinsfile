pipeline {
    agent {
        label 'aws'
    }

    stages {
        stage('Clone Source') {
            steps {
                checkout scmGit(
                    branches: [[name: '*/main']],
                    userRemoteConfigs: [[url: 'https://github.com/Mys7erio/spotify-xray']]
                )
            }
        }

        stage('Setup Metadata') {
            steps {
                script {
                    // Extracting the Git SHA to pass into the bake file
                    env.TAG = sh(script: 'git rev-parse --short HEAD', returnStdout: true).trim()
                }
                echo "Building Image Tag: ${env.TAG}"
            }
        }

        stage('Build & Push (Multi-Arch)') {
            steps {
                withCredentials([usernamePassword(
                    credentialsId: 'dockerhub-creds-271122',
                    passwordVariable: 'PASS',
                    usernameVariable: 'USER'
                )]) {
                    sh """
                        echo $PASS | docker login -u $USER --password-stdin
                        
                        # Docker buildx bake automatically picks up 'TAG' from the environment
                        docker buildx bake -f docker-bake.hcl --push
                        
                        docker logout
                    """
                }
            }
        }
    }

    post {
        always {
            // Native Jenkins step, no plugin required
            deleteDir()
        }
    }
}