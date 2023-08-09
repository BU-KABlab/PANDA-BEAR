import obsws_python as obs


# pass conn info if not in config.toml
cl = obs.ReqClient(host='localhost', port=4455, password='mystrongpass', timeout=3)

# Toggle the mute state of your Mic input
cl.toggle_input_mute('Mic/Aux')
cl.start_stream()
cl.stop_stream()
cl.get_stream_status()
cl.start_record()
cl.pause_record()

# Set the text of a text source
label = cl.get_input_settings("text")
label.input_settings["text"]="A5"
label.input_settings["font"]["size"]=70
cl.set_input_settings("text",label.input_settings,True)