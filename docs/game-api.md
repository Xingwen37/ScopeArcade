# 游戏包 API 1

游戏包目录至少包含 `game.json` 和 `game.py`；入口可以通过相对导入使用同目录辅助模块。每个包在独立模块命名空间加载，切换时重新创建实例。

```json
{"api_version":1,"id":"my-game","name":"我的游戏","entry":"game.py","description":"简介","controls":"按键说明"}
```

入口必须提供 `create_game(context)`，返回具有三个方法的对象：

```python
class Game:
    def update(self, dt, held, pressed):
        # dt 为秒。held 为按住键集合；pressed 为本次新按下键集合。
        # 键名小写：space、left、right、up、down、a、d 等。
        pass

    def lines(self):
        # 必须返回 1～72 条线段；每个坐标是 0～255 的 Python int。
        # X 向右增加，Y 向上增加；不能返回 NaN/浮点数/越界坐标。
        return [(20, 20, 200, 200)]

    def status(self):
        return "显示在游戏预览下方的文字"

def create_game(context):
    return Game()
```

`context.data_dir` 是此游戏可写的数据目录，`context.player_name` 是当前昵称，`context.sound(name)` 可播放 count/go/pass/crash/finish 五种简短音效，自动遵守静音开关。游戏不应直接读写应用目录；也不应打开串口、配置仪器或启动后台发送线程。

宿主以120Hz固定步进更新游戏、目标60Hz生成画面。`pressed` 只交付一次，按住键用 `held`。切换/停止/失焦会释放按键。游戏异常或无效画面会停止发送；绘图器约1秒后自行消隐，宿主仍可切换其他游戏。

安装包包含 Python 标准库中宿主使用的模块和内置依赖，不保证任意第三方库可用。首版外部游戏建议仅使用标准库；新增额外依赖需要维护者重新打包。

每条线段使用相同显示时间。长线可拆成数段来平衡亮度，但总数仍不得超过72。不要把高精度像素图逐像素展开；请使用轮廓和线框。安装 `game-template` 可检查添加、切换和输入的完整流程。
