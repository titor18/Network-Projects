import Router
from netmiko import ConnectHandler
from templates import radio_template

class CellRouter(Router):
    def __init__(self, ip_address, credentials):
        super().__init__(ip_address, credentials)


    def execute_commands(self):
        results = super().execute_commands()
        with ConnectHandler(**self.handler) as net_connect:
            radio_output = net_connect.send_command("Show cellular 0/1/0 radio", use_ttp=True, ttp_template=radio_template)
            results["cell_levels"] = radio_output
        return results


    def cell_levels(self, levels):
        """
        This function extracts and formats cellular signal parameters. 

        Parameters
        ----------
        levels : List 
            List that contains the output of the "show cellular0/1/0 radio" command.

        Returns
        -------
        None
        """
        levels = levels[0][0]
        signal_parameters = (
            f"Signal Parameters:\n"
            f"\tRSSI: {levels.get('RSSI')}\n"
            f"\tRSRP: {levels.get('RSRP')}\n"
            f"\tRSRQ: {levels.get('RSRQ')}\n"
            f"\tChannel: {levels.get('rx_channel')}\n"
            f"\tRAT: {levels.get('RAT_selected')}\n")
        Router.output_dict["cell_levels"] = signal_parameters
