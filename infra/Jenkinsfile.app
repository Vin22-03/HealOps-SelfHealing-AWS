pipeline {
  agent any

  environment {
    AWS_REGION     = "us-east-1"
    ECR_REPO_NAME  = "healops-app"
    AWS_ACCOUNT_ID = "987686462469"   // your account
  }

  stages {

    stage('Checkout') {
      steps {
        checkout scm
      }
    }

    stage('Build Docker Image') {
      steps {
        sh '''
          docker build -t healops-app .
        '''
      }
    }

    stage('Login to ECR') {
      steps {
        withCredentials([
          [$class: 'AmazonWebServicesCredentialsBinding',
           credentialsId: 'aws-healops']
        ]) {
          sh '''
            aws ecr get-login-password --region $AWS_REGION \
            | docker login --username AWS --password-stdin \
              $AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com
          '''
        }
      }
    }

    stage('Tag & Push Image') {
      steps {
        sh '''
          docker tag healops-app:latest \
            $AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com/$ECR_REPO_NAME:latest

          docker push \
            $AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com/$ECR_REPO_NAME:latest
        '''
      }
    }
  }

  post {
    success {
      echo "✅ HealOps app image pushed to ECR successfully"
    }
    failure {
      echo "❌ App build/push failed"
    }
  }
}
