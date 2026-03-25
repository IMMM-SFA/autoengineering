pipeline {
    agent any

    environment {
        PIXI_HOME = "${WORKSPACE}/.pixi"
    }

    stages {
        stage('Setup') {
            steps {
                sh '''
                    # Install pixi if not available
                    if ! command -v pixi &> /dev/null; then
                        curl -fsSL https://pixi.sh/install.sh | bash
                        export PATH="$HOME/.pixi/bin:$PATH"
                    fi

                    pixi install
                    pixi run install
                '''
            }
        }

        stage('Lint') {
            steps {
                sh 'pixi run lint'
            }
        }

        stage('Test') {
            steps {
                sh 'pixi run test'
            }
            post {
                always {
                    junit allowEmptyResults: true, testResults: 'results.xml'
                }
            }
        }

        stage('Examples') {
            parallel {
                stage('Hydro Chain') {
                    steps {
                        sh 'pixi run python examples/hydro_chain/run_workflow.py'
                    }
                }
                stage('Signal Chain') {
                    steps {
                        sh 'pixi run python examples/signal_chain/run_workflow.py'
                    }
                }
                stage('Lotka-Volterra') {
                    steps {
                        sh 'pixi run python examples/lotka_volterra/run_workflow.py'
                    }
                }
                stage('Leaf River') {
                    steps {
                        sh 'pixi run python examples/leaf_river/run_workflow.py'
                    }
                }
            }
        }
    }

    post {
        always {
            archiveArtifacts artifacts: 'results.xml', allowEmptyArchive: true
        }
        cleanup {
            cleanWs()
        }
    }
}
