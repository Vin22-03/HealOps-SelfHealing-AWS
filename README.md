#  HealOps – AWS Cloud Reliability & Self-Healing Incident Platform

HealOps is a **cloud-native reliability and failure-observation platform** built on AWS.  
It captures real failures from ECS, stores them in DynamoDB, measures MTTR, and visualizes the entire incident lifecycle through a sleek FastAPI dashboard.

No mocks.  
No fake data.  
No simulated timestamps.  
**Everything displayed comes directly from AWS-managed events.**

---

## What HealOps Demonstrates

### ✔️ Real ECS task failures captured automatically  
If a task stops, crashes, fails health checks, or fails deployment, AWS emits an event — HealOps records it.

### ✔️ ALB health check failures  
Unhealthy containers → ALB marks unhealthy → ECS stops task → new task launched.

### ✔️ Automatic AWS recovery  
ECS Scheduler replaces tasks instantly to maintain desired count.

### ✔️ MTTR calculated from REAL timestamps  
Detection time = EventBridge event  
Recovery time = ECS steady state  
MTTR = healed_time − detection_time

Most recoveries occur within **1–2 seconds**.

### ✔️ DynamoDB as the system of record  
Every incident is stored with structured metadata:

- incident type  
- failure reason  
- detection timestamp  
- recovery timestamp  
- MTTR  
- cluster, task ARN, exit code, etc.  

### ✔️ FastAPI dashboard  
Front-end mirrors DynamoDB in real time — no artificial UI assumptions.

---

## 🏛️ Architecture (Mermaid Diagram)

```mermaid
flowchart TD

A[User / Browser] -->|Dashboard| B[FastAPI App]

subgraph API["FastAPI Backend"]
    B -->|Fetch| C[DynamoDB - Incident Store]
end

subgraph Runtime["ECS Runtime"]
    H[Application Container] -->|Health Check| ALB
    ALB[Application Load Balancer] --> H
end

subgraph Events["AWS Event Layer"]
    ECS[ECS Service] -->|Task Stopped / Unhealthy| EventBridge
    EventBridge --> Lambda[AWS Lambda - Incident Processor]
    Lambda -->|Write Incident| C
    ECS -->|Launch Replacement Task| H
end

```
#  Project Components

### **1️⃣ ECS Fargate**
- Runs the application container  
- Integrates with ALB for health checks  
- Replaces failing tasks automatically  

### **2️⃣ ALB**
- Performs `/health` checks  
- Marks tasks unhealthy → triggers stop & replacement  

### **3️⃣ EventBridge**
Captures:
- ECS Task STOPPED  
- Health check failures  
- Deployment failures  
- Essential containers exiting  

### **4️⃣ AWS Lambda**
Lightweight ingestion engine:
- Parses ECS events  
- Classifies the incident  
- Saves record to DynamoDB  
- Identifies recovery and calculates MTTR  

### **5️⃣ DynamoDB**
Stores the entire incident history:
service, incident_type, failure_reason, detection_time,
healed_time, mttr_seconds, healing_action, cluster, task_arn…

### **6️⃣ FastAPI**
- Dashboard APIs  
- Incidents API  
- UI rendering  

### **7️⃣ Terraform IaC**
Creates all AWS infrastructure:
- VPC  
- Subnets  
- ECS Cluster  
- Task Definition  
- ALB  
- Target Group  
- EventBridge Rule  
- IAM Roles  
- DynamoDB Table  
- Lambda Function  

### **8️⃣ Jenkins CI/CD**
Build → ECR push → ECS deploy pipeline.

---

#  Project Screenshots

| # | Screenshot | Description |
|---|------------|-------------|
| **1** | ![](ScreenShots/HealOps%20Dashboard.png) | **Main Dashboard** showing MTTR, detection summary, latest incident |
| **2** | ![](ScreenShots/HealOps%20Incidents.png) | **Complete Incident Timeline** with healing details & statuses |
| **3** | ![](ScreenShots/Failure%20reason.png) | **Failure Reason Details** extracted from real AWS events |
| **4** | ![](ScreenShots/Healthcheck_failure.png) | **ALB Health Check Failure Evidence** showing unhealthy container |
| **5** | ![](ScreenShots/CPU%20alarm.png) | **CloudWatch CPU Alarm Trigger** used for automatic detection |
| **6** | ![](ScreenShots/DynamoDB_Table.png) | **DynamoDB Incident Store** containing MTTR and lifecycle metadata |
| **7** | ![](ScreenShots/ECS_Cluster.png) | **ECS Cluster Overview** where the HealOps service runs |
| **8** | ![](ScreenShots/ECS_Tasks.png) | **ECS Tasks View** showing failures & service-driven task replacement |
| **9** | ![](ScreenShots/EventBridge%20Rules.png) | **EventBridge Rules** capturing ECS task failures & CloudWatch alarms |
| **10** | ![](ScreenShots/HealOps%20About.png) | **About Page** explaining architecture & design details |


---

#  Incident Behavior Supported

| Failure Type | Cause | Detection | Healing |
|--------------|-------|-----------|---------|
| HEALTH_CHECK_FAILURE | ALB health check failed | EventBridge ECS event | ECS launches new task |
| DEPLOYMENT_FAILURE | Bad image / startup crash | ECS Task STOPPED | ECS rollback / new task |
| TASK_STOPPED | Manual or forced stop | ECS STOPPED event | ECS scheduler |
| CONTAINER_CRASH | Essential container exit | STOPPED | Replacement task |

Every incident includes:
- Failure reason  
- Detection time  
- Recovery time  
- MTTR  
- Healing action  

---
#  CI/CD Deployment Flow

1. Code pushed to GitHub  
2. Jenkins triggers pipeline  
3. Builds Docker image  
4. Pushes image to Amazon ECR  
5. Updates ECS service with new task revision  
6. ALB validates new task health  
7. HealOps dashboard displays real-time incidents  

---

#  Failure Injection (Real AWS Behavior)

HealOps provides safe URLs to intentionally break the app:

| Endpoint | Behavior |
|----------|----------|
| `/inject/crash` | Crashes the container instantly |
| `/inject/unhealthy` | ALB marks task unhealthy |
| `/inject/hang` | Simulates freeze |

Each one produces a **real AWS incident** logged into DynamoDB.

---

#  MTTR (Mean Time To Recovery)

MTTR = healed_time − detection_time  

Typical values observed:

| Incident | MTTR |
|----------|------|
| Health Check Failure | 1–2 seconds |
| Crash / Stop | 1 second |
| Deployment Issues | 1–3 seconds |

ECS is highly optimized for quick auto-healing, which HealOps visualizes clearly.

---

#  API Endpoints

### **GET `/api/dashboard`**
Returns:
- total_incidents  
- MTTR  
- latest incident  
- open/resolved counts  

### **GET `/api/incidents`**
Returns full structured incident history.

### **GET `/health`**
Used by ALB to determine task health.

### **GET `/inject/*`**
Controlled failure simulation.

---

#  Key Cloud & DevOps Skills Demonstrated

- AWS ECS Fargate  
- ALB health management  
- EventBridge event-driven architecture  
- AWS Lambda event ingestion  
- DynamoDB NoSQL modelling  
- CI/CD with Jenkins  
- Terraform IaC  
- FastAPI API design  
- MTTR measurement from real AWS signals  
- Observability & cloud reliability mindset  

---

**Vinay V Bhajantri**  
Cloud & DevOps Engineer  
- GitHub: https://github.com/Vin22-03  
- Portfolio: https://vincloudops.tech  
- LinkedIn: https://linkedin.com/in/vinayvbhajantri  

---

#  Final Note

HealOps reflects the real operational behaviour of AWS-managed systems.  
Failures are real. Detection is real. Recovery is real.  
Nothing is mocked or simulated.



