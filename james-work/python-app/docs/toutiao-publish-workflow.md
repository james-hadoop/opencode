# 今日头条文章发布流程文档

> 最后更新: 2026-04-02
> 观察方式: Playwright 浏览器自动化

## 发布成功后的页面状态

### 关键特征（用于自动化检测）

1. **页面 URL 不变**: `https://mp.toutiao.com/profile_v4/graphic/publish`
2. **表单清空**: 标题和正文输入框变为空
3. **草稿保存**: 左侧显示 "草稿" - 刚发布的文章标题
4. **底部按钮仍在**: "预览并发布" 按钮仍然可见

### 页面元素快照（发布后）

```yaml
- generic [active]:
    - main:
        - generic:
            # 草稿区域显示刚发布的文章
            - generic [cursor=pointer]:
                - generic:
                    - generic: 草稿
                    - generic: 马斯克亲自点赞，Kimi动了十一年没人敢碰的东西 - 今日头
                - button "继续编辑"
            # 表单已清空
            - textbox "请输入文章标题（2～30个字）" # 为空
            - paragraph: 请输入正文 # 为空
            # 底部按钮
            - button "预览"
            - button "定时发布"
            - button "预览并发布"
```

## 自动化检测建议

### 方法1: 检测草稿出现

发布后检查左侧是否出现"草稿"区域，包含刚发布的标题。

### 方法2: 检测表单清空

发布后标题输入框内容变为空（或 placeholder 重新出现）。

### 方法3: 不依赖页面状态

发布后直接跳转到内容管理页面验证：

- URL: `https://mp.toutiao.com/profile_v4/manage/content/all`
- 检查文章是否出现在列表中

## 代码修改建议

修改 `_wait_for_publish_complete()` 函数：

```python
def _wait_for_publish_complete(self) -> bool:
    # ... 现有等待逻辑 ...

    # 新增：检测发布成功
    page_text = self.page.content()

    # 方法1: 检查草稿区域
    if "草稿" in page_text and "马斯克" in page_text:
        log("检测到草稿保存，发布成功")
        self._take_debug_screenshot("publish_success")
        return True

    # 方法2: 检查表单是否被清空（标题 placeholder 重新出现）
    if "请输入文章标题" in page_text:
        title_input = self.page.locator('input[placeholder*="标题"]')
        if title_input.is_visible(timeout=2000):
            log("表单已重置，发布成功")
            self._take_debug_screenshot("publish_success")
            return True

    return False
```

## 发布流程回顾

1. ✅ 填写标题
2. ✅ 填写正文（编辑器）
3. ✅ 插入图片
4. ✅ 选择封面图
5. ✅ 选择分类
6. ✅ 点击"预览并发布"按钮
7. ✅ **发布成功** → 页面返回发布表单，草稿保存成功
