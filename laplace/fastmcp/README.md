注意：使用FastMCP时候不要开启系统网络代理！
制作镜像
```bash
docker build -t laplace-mcp .
```
启动容器
```bash
docker run -d -i --name laplace-mcp -p 8080:8080 laplace-mcp
```