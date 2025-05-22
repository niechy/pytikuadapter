# pytikuadapter
[tikuadapter](https://github.com/DokiDoki1103/tikuAdapter)的python版，从自己的角度加了些东西

现在还是毛胚，目前简单实现了查询多题库的功能，返回都还是直接json

Todo（大致按优先级排序）

- [ ] 更多网络题库
- [ ] 返回统一处理
- [ ] 异常处理
- [ ] 本地缓存
- [ ] 鉴权
- [ ] WebUI
- [ ] 文件题库解析


POST http://localhost:8000/adapter-service/search

请求体

```
{
  "question": "毛泽东思想形成的时代背景是( )",
  "options": [
    "帝国主义战争与无产阶级革命成为时代主题",
    "和平与发展成为时代主题",
    "世界多极化成为时代主题",
    "经济全球化成为时代主题"
  ],
  "type": 0,// 单选0多选1填空2判断3问答4
  "token":""//目前没用
  "use": {
    "Tikuhai": {
      "key": "*****"
    },
    "Enncy": {
      "token": "*******"
    },
    "Like": {
      "token": "*****"
      "model": "deepseek-v3"
    }
  }
}
```
与原版不同的是将url请求参数移到了请求体中

响应体目前与原版无区别

作者是一名非计算机系大学生，代码纯菜，边写边学的，欢迎吐槽、issue，PR。

同时感谢一众大模型Deepseek，Grok，阿里灵码

License会在项目完善点后再弄