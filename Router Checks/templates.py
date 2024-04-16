#used to parse with TTP the commands that cannot be parsed with TextFSM

bfd_template = """<group method="table">
{{ neighbor_address | IP }} {{ignore}} {{ignore}} {{state}} {{interface}}
</group> """

flow_template_4331 = """
Flow Exporter {{name}}:
  Description:              {{ignore}}
  Export protocol:          {{ignore}}
  Transport Configuration:
    Destination IP address: {{destination_address}}
    Source IP address:      {{ignore}}
    Source Interface:       {{source_interface}}
    Transport Protocol:     {{transport_protocol}}
    Destination Port:       {{destination_port}}"""

radio_template = """
Radio power mode = {{radio_status}}
LTE Rx Channel Number(PCC) =  {{rx_channel}}
LTE Tx Channel Number(PCC) =  {{tx_channel}}
LTE Band =  {{lte_band}}
LTE Bandwidth = {{lte_bandwidth | ORPHRASE}}
Current RSSI = {{RSSI | ORPHRASE}}
Current RSRP = {{RSRP | ORPHRASE}}
Current RSRQ = {{RSRQ | ORPHRASE}}
Current SNR = {{SNR | ORPHRASE}}
Physical Cell Id = {{cell_id}}
Number of nearby cells = {{cells_nearby}}
{{ignore}}
Radio Access Technology(RAT) Preference = {{mode}}
Radio Access Technology(RAT) Selected = {{RAT_selected}}
{{ignore}}"""