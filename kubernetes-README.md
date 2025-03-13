# ForeFlight Logbook Kubernetes Deployment

This document provides instructions for deploying the ForeFlight Logbook application to a Kubernetes cluster.

## Prerequisites

- A Kubernetes cluster (local or cloud-based)
- `kubectl` command-line tool installed and configured to communicate with your cluster
- Docker Hub account (if you need to build and push your own image)

## Deployment Options

Two deployment configurations are provided:

1. `deployment.yaml` - Full deployment with Ingress for production environments
2. `deployment-local.yaml` - Simplified deployment with NodePort for local development

## Deploying to Kubernetes

### Option 1: Full Deployment with Ingress

This option is suitable for production environments with an Ingress controller.

```bash
kubectl apply -f deployment.yaml
```

After deployment, you can access the application at `http://foreflight.local` (modify the hostname in the Ingress resource as needed).

### Option 2: Local Deployment with NodePort

This option is suitable for local development environments like Minikube or Docker Desktop Kubernetes.

```bash
kubectl apply -f deployment-local.yaml
```

After deployment, you can access the application using:

```bash
# Get the NodePort assigned to the service
kubectl get svc -n foreflight-logbook

# Access the application at http://localhost:<NodePort>
```

## Verifying the Deployment

```bash
# Check if the namespace was created
kubectl get ns foreflight-logbook

# Check if the PVCs were created
kubectl get pvc -n foreflight-logbook

# Check if the deployment is running
kubectl get deployments -n foreflight-logbook

# Check if the pods are running
kubectl get pods -n foreflight-logbook

# Check if the service is available
kubectl get svc -n foreflight-logbook

# If using Ingress, check if it's configured
kubectl get ingress -n foreflight-logbook
```

## Accessing Logs

```bash
# Get the pod name
kubectl get pods -n foreflight-logbook

# View logs
kubectl logs -n foreflight-logbook <pod-name>
```

## Customizing the Deployment

### Using Your Own Image

If you want to use your own image, modify the `image` field in the deployment file:

```yaml
containers:
- name: foreflight-logbook
  image: your-username/foreflight-logbook:your-tag
```

### Adjusting Resource Limits

Modify the `resources` section in the deployment file to adjust CPU and memory limits:

```yaml
resources:
  limits:
    cpu: "500m"    # 0.5 CPU cores
    memory: "512Mi"  # 512 MB RAM
  requests:
    cpu: "200m"    # 0.2 CPU cores
    memory: "256Mi"  # 256 MB RAM
```

### Scaling the Application

To scale the application, adjust the `replicas` field in the deployment file or use the `kubectl scale` command:

```bash
kubectl scale deployment foreflight-logbook -n foreflight-logbook --replicas=3
```

## Cleaning Up

To remove the deployment:

```bash
# For full deployment
kubectl delete -f deployment.yaml

# For local deployment
kubectl delete -f deployment-local.yaml
```

## Troubleshooting

### Pod Not Starting

Check the pod status and events:

```bash
kubectl describe pod -n foreflight-logbook <pod-name>
```

### Service Not Accessible

Check the service and endpoints:

```bash
kubectl describe svc -n foreflight-logbook foreflight-logbook
kubectl get endpoints -n foreflight-logbook foreflight-logbook
```

### PersistentVolumeClaim Not Binding

Check the PVC status:

```bash
kubectl describe pvc -n foreflight-logbook foreflight-logs-pvc
kubectl describe pvc -n foreflight-logbook foreflight-uploads-pvc
``` 