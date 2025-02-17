# 部署指南

## 环境要求
- Kubernetes 1.21+
- Docker 20.10+
- AWS Fargate 配置

## 部署步骤
1. 构建Docker镜像：
```bash
docker build -t option-system .
```

2. 推送至镜像仓库：
```bash
docker tag option-system:latest registry.example.com/option-system:v1.3
docker push registry.example.com/option-system:v1.3
```

3. 应用Kubernetes配置：
```bash
kubectl apply -f deploy/k8s/
```

4. 验证部署状态：
```bash
kubectl get pods -l app=option-system
``` 