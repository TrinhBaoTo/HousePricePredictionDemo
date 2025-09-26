pipeline {
    agent any

    environment {
        APP_NAME = 'house-price-flask'
        IMAGE_NAME = "house-price-flask"
        IMAGE_TAG  = "${env.BUILD_NUMBER}"
        PYTHON = 'python3'
        VENV_DIR = '.venv'
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

        stage('Unit Tests') {
            steps {
                sh '''
                ${PYTHON} -m venv ${VENV_DIR}
                . ${VENV_DIR}/bin/activate
                pip install --upgrade pip wheel
                pip install -r requirements.txt
                pip install pytest pytest-cov

                export PYTHONPATH=$PWD 
                pytest -q --maxfail=1 --disable-warnings \
                    --cov=app --cov-report=xml:coverage.xml \
                    --junitxml=pytest-report.xml
                '''
            }
            post {
                always {
                junit allowEmptyResults: true, testResults: 'pytest-report.xml'
                archiveArtifacts allowEmptyArchive: true, artifacts: 'coverage.xml'
                }
            }
        }

stage('Security - Code (Bandit)') {
  steps {
    sh '''
      . ${VENV_DIR}/bin/activate || { ${PYTHON} -m venv ${VENV_DIR}; . ${VENV_DIR}/bin/activate; }

      pip install --quiet --upgrade bandit
      bandit -r app -f json -o bandit.json || true

      # parse+fail on HIGH
      cat > parse_bandit.py <<'PY'
import json, sys
d = json.load(open("bandit.json")) if __import__("pathlib").Path("bandit.json").exists() else {"results":[]}
sev = {"LOW":0,"MEDIUM":0,"HIGH":0}
for r in d.get("results", []):
    sev[r.get("issue_severity","LOW").upper()] = sev.get(r.get("issue_severity","LOW").upper(),0) + 1
print(f"[Bandit] High:{sev['HIGH']}  Medium:{sev['MEDIUM']}  Low:{sev['LOW']}")
if sev['HIGH'] > 0:
    print("Why failed: HIGH severity code issues. Fix or add justified '# nosec'.")
    sys.exit(2)
PY
      python3 parse_bandit.py
    '''
  }
  post {
    always { archiveArtifacts artifacts: 'bandit.json', allowEmptyArchive: true }
  }
}

stage('Security - Deps (pip-audit)') {
  steps {
    sh '''
      . ${VENV_DIR}/bin/activate || { ${PYTHON} -m venv ${VENV_DIR}; . ${VENV_DIR}/bin/activate; }

      pip install --quiet --upgrade pip-audit
      # JSON output to file; stdout warnings go to console, not the file
      pip-audit -r requirements.txt -f json -o pip-audit.json || true

      cat > parse_pipaudit.py <<'PY'
import json, sys, pathlib

p = pathlib.Path("pip-audit.json")
if not p.exists() or p.stat().st_size == 0:
    print("[pip-audit] No report generated.")
    sys.exit(0)

def count_findings(obj):
    """Return (critical, high) from various pip-audit JSON shapes."""
    crit = hi = 0

    # Case A: list of deps OR list of strings (edge)
    if isinstance(obj, list):
        for item in obj:
            if isinstance(item, dict):
                for v in item.get("vulns", []):
                    sev = (v.get("severity") or "").upper()
                    if sev == "CRITICAL": crit += 1
                    elif sev == "HIGH": hi += 1
            # if it’s a string ignore
        return crit, hi

    # Case B: dict with dependencies:[{..., vulns:[...]}]
    if isinstance(obj, dict):
        deps = obj.get("dependencies") or obj.get("results") or []
        if isinstance(deps, list):
            for dep in deps:
                if not isinstance(dep, dict):
                    continue
                for v in dep.get("vulns", []):
                    sev = (v.get("severity") or "").upper()
                    if sev == "CRITICAL": crit += 1
                    elif sev == "HIGH": hi += 1
        # Case C: dict with top-level "vulnerabilities":[...] (future schemas)
        for v in obj.get("vulnerabilities", []):
            sev = (v.get("severity") or "").upper()
            if sev == "CRITICAL": crit += 1
            elif sev == "HIGH": hi += 1
        return crit, hi

    # Anything else: treat as no findings
    return 0, 0

try:
    data = json.load(open(p))
except Exception as e:
    print(f"[pip-audit] Could not parse JSON: {e}")
    sys.exit(0)

crit, hi = count_findings(data)
print(f"[pip-audit] Findings — Critical:{crit} High:{hi}")
if crit + hi > 0:
    print("\\nWhy failed: Vulnerable dependencies detected. Fix by pinning/upgrading in requirements.txt.")
    sys.exit(2)
PY
      python3 parse_pipaudit.py
    '''
  }
  post {
    always { archiveArtifacts artifacts: 'pip-audit.json', allowEmptyArchive: true }
  }
}

stage('Security - Secrets (Gitleaks)') {
  steps {
    sh '''
      docker run --rm -v "$PWD:/repo" zricethezav/gitleaks:latest detect \
        --source=/repo --report-format=json --report-path=/repo/gitleaks.json || true

      cat > parse_gitleaks.py <<'PY'
import json, sys, os
rp = 'gitleaks.json'
if not os.path.exists(rp) or os.path.getsize(rp) == 0:
    print("[Gitleaks] No report.")
    sys.exit(0)
try:
    data = json.load(open(rp))
    count = len(data) if isinstance(data, list) else int(data.get("total", 0))
except Exception:
    count = 0
print(f"[Gitleaks] Potential secrets: {count}")
if count > 0:
    print("\\nWhy failed: Possible hardcoded secrets. Remove from repo, rotate keys, use env vars.")
    sys.exit(2)
PY
      python3 parse_gitleaks.py
    '''
  }
  post {
    always { archiveArtifacts artifacts: 'gitleaks.json', allowEmptyArchive: true }
  }
}

        stage('SonarCloud Analysis') {
            steps {
                withSonarQubeEnv('SonarCloud') {
                script {
                    def scannerHome = tool name: 'SonarScanner-macos-arm64', type: 'hudson.plugins.sonar.SonarRunnerInstallation'
                    sh """
                    PATH="${scannerHome}/bin:\$PATH" sonar-scanner
                    """
                }
                }
            }
        }
        stage('Quality Gate') {
            steps {
                timeout(time: 3, unit: 'MINUTES') {
                waitForQualityGate abortPipeline: true
                }
            }
        }

        stage('Deploy') {
            steps {
                sh """
                CONTAINER_ID=$(docker ps -q --filter "publish=5000")
                    if [ ! -z "$CONTAINER_ID" ]; then
                        docker rm -f $CONTAINER_ID
                    fi

                echo "Deploying ${IMAGE_NAME}:${IMAGE_TAG} locally"

                # stop old container if exists
                docker rm -f ${APP_NAME} || true

                # run new one
                docker run -d --name ${APP_NAME} -p 5000:5000 ${IMAGE_NAME}:${IMAGE_TAG}

                echo "App running at http://localhost:5000"
                """
            }
        }
        
        stage('Release') {
            steps {
                withCredentials([usernamePassword(credentialsId: 'dockerhub-creds', usernameVariable: 'DOCKER_USER', passwordVariable: 'DOCKER_PASS')]) {
                    sh '''
                        echo "Logging into Docker Hub..."
                        echo "$DOCKER_PASS" | docker login -u "$DOCKER_USER" --password-stdin

                        echo "Tagging image for Docker Hub..."
                        docker tag ${IMAGE_NAME}:${IMAGE_TAG} $DOCKER_USER/${IMAGE_NAME}:${IMAGE_TAG}
                        docker tag ${IMAGE_NAME}:${IMAGE_TAG} $DOCKER_USER/${IMAGE_NAME}:latest

                        echo "Pushing image to Docker Hub..."
                        docker push $DOCKER_USER/${IMAGE_NAME}:${IMAGE_TAG}
                        docker push $DOCKER_USER/${IMAGE_NAME}:latest
                    '''
                }
            }
        }
    }
}
