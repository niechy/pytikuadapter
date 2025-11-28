# pytikuadapter
[tikuadapter](https://github.com/DokiDoki1103/tikuAdapter)的python版，从自己的角度加了些东西

现在还是毛胚，目前简单实现了查询多题库的功能

如果想要加入更多题库，可以看看adapter/like.py

支持的题库：
- Like知识库


阿巴阿巴重新写了，下面的还没写
- 言溪题库
- 题库海题库
- Lemon题库
- 万能题库
- everyapi/GO题/icodef
- AXE题库
- Zerror题库
- Zxseek/知寻题库
- Zero题库
- 硅基流动

排名不分先后

Todo（大致按优先级排序）

- [x] 更多网络题库（持续增加）
- [x] 返回统一处理
- [ ] 异常处理
- [ ] 本地缓存
- [ ] 鉴权
- [ ] WebUI
- [ ] 文件题库解析


POST http://localhost:8000/v1/adapter-service/search

headers
```
Content-Type: application/json
Authorization: Bearer your_token_here
```

请求体

```json
{
  "query":{
  "content": "毛泽东思想形成的时代背景是( )",
  "options": [
    "帝国主义战争与无产阶级革命成为时代主题",
    "和平与发展成为时代主题", 
    "世界多极化成为时代主题",
    "经济全球化成为时代主题"
  ],
  "type": 0
  },
  "providers": [
    {
      "name": "Tikuhai",
      "config": {
        "api_key": "*****"
      }
    },
    {
      "name": "Enncy",
      "config": {
        "token": "*******"
      }
    },
    {
      "name": "Like知识库",
      "config": {
        "key": "**************",
        "model": "deepseek-v3.2"
      }
    }
  ]
}
```
与原版区别还是有点，不破不立嘛（大概）

整个分为两块query和providers

query部分是题目相关，providers部分是题库相关

后续可能再加一块，重试次数，总超时时间，以及聚合策略之类

响应体感觉还会改，目前是这样的
```json
{
    "query": {
        "content": "毛泽东思想形成的时代背景是( )",
        "options": [
            "帝国主义战争与无产阶级革命成为时代主题",
            "和平与发展成为时代主题",
            "世界多极化成为时代主题",
            "经济全球化成为时代主题"
        ],
        "type": 0
    },
    "unified_answer": {
        "answerKey": [
            "A"
        ],
        "answerKeyText": "A",
        "answerIndex": [
            0
        ],
        "answerText": "帝国主义战争与无产阶级革命成为时代主题",
        "bestAnswer": [
            "帝国主义战争与无产阶级革命成为时代主题"
        ]
    },
    "provider_answer": [
        {
            "provider": "Like知识库",
            "type": 0,
            "choice": [
                "A"
            ],
            "judgement": null,
            "text": null
        }
    ],
    "successful_providers": 1
}
```

作者是一名非计算机系大学生，代码纯菜，边写边学的，欢迎吐槽、issue，PR。

同时感谢一众大模型Deepseek，Grok，阿里灵码

License会在项目完善点后再弄