# Etapa 1: Build
FROM node:18-alpine as build
WORKDIR /app
COPY package.json ./
COPY package-lock.json ./
RUN npm install
COPY . .
RUN npm run build

# Etapa 2: Servir con Nginx
FROM nginx:alpine
# Copiamos el build de React a la carpeta de Nginx
COPY --from=build /app/build /usr/share/nginx/html
# Exponer puerto 80 interno
EXPOSE 80
CMD ["nginx", "-g", "daemon off;"]