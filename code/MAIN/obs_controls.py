import obsws_python as obsws

class OBS_controller():
      def __init__(self):
         self.client = obsws.ReqClient(host='localhost', port=4455, password='PandaBear!', timeout=3)

      def place_text_on_screen(self, instructions):
        video_information = f'''
            Experiment Parameters:
                Experiment ID: {instructions["id"]}
                Status: {instructions["status"]}
                Well: {instructions["target_well"]}
                Replicates: {instructions["replicates"]}
                DMF: {instructions["dmf"]}
                PEG: {instructions["peg"]}
                Acrylate: {instructions["acrylate"]}
                Ferrocene: {instructions["ferrocene"]}
                Custom: {instructions["custom"]}
                Deposition Voltage: {instructions["dep-pot"]}
                OCP Compelte: No
                Deposition Complete: No
                Characterization Complete: No
               '''
        label = self.client.get_input_settings("text")
        label.input_settings["text"]=video_information
        label.input_settings["font"]["size"]=40
        self.client.set_input_settings("text",label.input_settings,True)

        def webcam_on(self):
            webcam = self.client.get_input_settings("Webcam")
            webcam.input_settings["sceneItemEnabled"]=True
            self.client.set_input_settings("Webcam",webcam.input_settings,True)

        def webcam_off(self):
            webcam = self.client.get_input_settings("Webcam")
            webcam.input_settings["sceneItemEnabled"]=False
            self.client.set_input_settings("Webcam",webcam.input_settings,True)

        
