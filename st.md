用户操作：
  点击 Explorer 界面中的 "返回" 按钮
        或
  双击 Explorer 界面中的目录图标

     ↓

Explorer.go_up_directory() 或 Explorer.handleDoubleClick()
  (根据操作类型和目标路径)

     ↓

Explorer.load_files(target_path)
  (检查 target_path 是否与 current_path 相同)
  
  ┌─────────────────────────────────────────────────────────────────────────────────────────────────────────────────────┐
  │ 情况1: target_path != current_path (需要切换目录)         │  情况2: target_path == current_path (只需刷新，例如双击".")
  └─────────────────────────────────────────────────────────────────────────────────────────────────────────────────────┘
          ↓                                                         ↓
Terminal.execute_command_for_explorer(f"cd {target_path}")          Terminal.run()
  (Terminal 发送 "cd" 命令到 Shell)                             (Terminal 发出 requestExplorerRefresh 信号)

          ↓                                                         ↓

Shell 执行 "cd" 命令                                         Explorer 接收 requestExplorerRefresh 信号
  (Shell 输出提示符)                                           并调用 load_current_terminal_directory()

          ↓                                                         ↓

Terminal 捕获 Shell 输出                                   Terminal.execute_command_for_explorer("ls -a")
  (在 _handle_api_for_explorer 中判断 "cd" 命令完成)       (Terminal 发送 "ls -a" 命令到 Shell)

          ↓                                                         ↓

Terminal 发出 explorerCommandOutputReady 信号               Shell 执行 "ls -a" 命令
  (command_type="cd")                                       (Shell 输出文件列表和提示符)

          ↓                                                         ↓

Explorer._handle_explorer_command_response()                Terminal 捕获 Shell 输出
  (确认 "cd" 成功)                                          (在 _handle_api_for_explorer 中判断 "ls -a" 命令完成)

          ↓                                                         ↓

Terminal.requestExplorerRefresh.emit()                     Terminal 发出 explorerCommandOutputReady 信号
  (请求刷新当前目录)                                          (command_type="ls")

          ↓                                                         ↓

Explorer 接收 requestExplorerRefresh 信号                      Explorer._handle_explorer_command_response()
  并调用 load_current_terminal_directory()                     (确认 "ls" 成功，调用 _parse_ls_output_and_populate_cards())

          ↓                                                         ↓

Terminal.execute_command_for_explorer("ls -a")              Explorer.clear_file_display()
  (Terminal 发送 "ls -a" 命令到 Shell)                       Explorer 遍历解析后的文件数据并调用 addFile()

          ↓

(同上，Shell 执行 "ls -a", Terminal 捕获输出,
  Explorer._handle_explorer_command_response() 处理 "ls" 输出)

          ↓

Explorer 更新 UI 显示文件列表