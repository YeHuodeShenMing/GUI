const express = require('express');
const path = require('path');
const RTSP2web = require('rtsp2web');
const app = express();
const port = 3000;

// 设置静态文件目录
app.use(express.static(path.join(__dirname, 'public')));

// 启动 RTSP2web 服务
const rtspServer = new RTSP2web({
  port: 9999,
  verbose: true
});

// 启动 Express 服务器
app.listen(port, () => {
  console.log(`Server running at http://localhost:${port}/`);
});