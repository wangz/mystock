# MyStock 项目工作流程规范

## 📋 发布流程

### ✅ 发布条件

**只有当用户明确要求时才发布**，否则只修改代码。

#### 需要发布的关键词：
- "推送到 GitHub"
- "发布到 ClawHub"
- "提交并发布"
- "push to github"
- "publish to clawhub"
- "deploy"

#### 不发布的场景：
- 日常代码修改
- Bug 修复
- 功能开发
- 文档更新
- 测试修改

## 🔄 工作流程

### 开发模式（不发布）

```
1. 修改代码/文档
2. git add . 
3. git commit -m "修改说明"
4. ❌ 不执行 git push
5. ❌ 不执行 clawhub publish
```

### 发布模式（用户明确要求）

```
1. 修改代码/文档
2. git add . && git commit -m "提交说明"
3. ✅ git push
4. ✅ clawhub publish --version X.X.X --changelog "更新说明"
5. ✅ 通知用户发布完成
```

## 📝 版本号规范

- 修复 Bug：1.0.x → 1.0.x+1
- 新功能：1.x.0 → 1.x+1.0
- 大版本：x.0.0 → x+1.0.0

## 🎯 示例

### ❌ 开发时不要说
- "修复了xxx问题" → 只 commit，不 push
- "添加了新功能" → 只 commit，不 push

### ✅ 发布时应该说
- "推送到 GitHub 并发布到 ClawHub"
- "提交并发布"
- "deploy to production"

## 📌 其他规则

- 代码修改后自动 commit
- 保持代码整洁
- 添加有意义的 commit message
- 先测试再发布

---

**创建时间**: 2026-03-28
**最后更新**: 2026-03-28
