# 前端镜像：构建上下文必须是仓库根目录（依赖 packages/simple-mind-map 本地包）
FROM node:20-alpine AS build
WORKDIR /repo
COPY packages/simple-mind-map/package.json packages/simple-mind-map/package-lock.json ./packages/simple-mind-map/
RUN npm ci --prefix ./packages/simple-mind-map --omit=dev
COPY packages/simple-mind-map ./packages/simple-mind-map
COPY frontend/package.json frontend/package-lock.json ./frontend/
WORKDIR /repo/frontend
RUN npm ci
COPY frontend ./
# 可选：注入自有文件服务的浏览器访问地址（默认不注入，走后端 /uploads）
RUN npm run build

FROM nginx:alpine
COPY --from=build /repo/frontend/dist /usr/share/nginx/html
COPY frontend/nginx.conf /etc/nginx/conf.d/default.conf
EXPOSE 80
