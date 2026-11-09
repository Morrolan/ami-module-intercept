// Intercept-owned wording. Shared mechanics live in ami/shared/ui/explain.js.
(function () {
  'use strict';
  const guide = /* catalogue */ {
  "aircraft-click-zoom": {
    "term": "Click zoom",
    "meaning": "ON moves and zooms the map to a selected aircraft. OFF keeps the map fixed while showing aircraft details and highlighting the selection.",
    "matters": "Keep your view of surrounding traffic when choosing aircraft on the map, in the list or through linked messages. This device remembers your choice.",
    "notMeaning": "Manual panning and zoom controls still work. Turning this off does not stop reception or aircraft updates.",
    "category": "Guide"
  },
  "title-Remote receivers": {
    "term": "Remote receivers",
    "meaning": "The one shared list of remote receivers, managed by admins. Each has a type; ADS-B feeds appear in the ADS-B device menu for everyone. Each host and port is checked about once a minute with a three-second deadline.",
    "matters": "Keeps remote receivers in one place and shows Online, Offline or Not checked yet and the last successful connection, without starting a receiver or sending alerts.",
    "notMeaning": "Online does not prove a receiver is decoding or sending data. A connection check can briefly occupy a single-client service such as rtl_tcp. Last seen resets when Intercept restarts or the entry is edited.",
    "category": "Guide"
  },
  "title-Teesside airport board": {
    "term": "Teesside airport board",
    "meaning": "Shows the airport's published arrivals, departures and estimates, plus separately received Draken aircraft.",
    "matters": "Use the next-movement countdowns to decide when to listen to local air traffic control.",
    "notMeaning": "The board is checked at most every five minutes and does not provide ATC clearances or a Draken flight timetable.",
    "category": "Guide"
  },
  "title-Listen to Teesside Tower": {
    "term": "Listen to Tower",
    "meaning": "Tunes your selected local airband receiver to the Tower carrier frequency, 119.800 MHz AM.",
    "matters": "The published 8.33 kHz channel name is 119.805; an SDR tunes the carrier frequency instead.",
    "notMeaning": "This is receive-only and requires a free receiver; opening the board does not start listening.",
    "category": "Guide"
  },
  "title-Listen to Teesside Approach": {
    "term": "Listen to Approach",
    "meaning": "Tunes your selected local airband receiver to the Approach carrier frequency, 118.850 MHz AM.",
    "matters": "The published 8.33 kHz channel name is 118.855; an SDR tunes the carrier frequency instead.",
    "notMeaning": "This is receive-only and reception depends on your receiver and antenna.",
    "category": "Guide"
  },
  "title-Aircraft route origin": {
    "term": "Origin",
    "meaning": "Departure airport from a public callsign-route lookup, when available.",
    "matters": "Provides context for the selected aircraft without changing its received position.",
    "notMeaning": "ADS-B does not transmit this field; a callsign route can be unavailable or differ from the current flight.",
    "category": "Guide"
  },
  "title-Aircraft route destination": {
    "term": "Destination",
    "meaning": "Arrival airport from a public callsign-route lookup, when available.",
    "matters": "Helps identify where the selected flight may be heading.",
    "notMeaning": "This is not a verified flight plan, arrival clearance or a route inferred from the aircraft's heading.",
    "category": "Guide"
  },
  "title-Aircraft colour key": {
    "term": "Aircraft key",
    "meaning": "Explains the colours, status rings and aircraft shapes used on the map.",
    "matters": "Use the key to distinguish altitude bands, ground traffic, military aircraft and emergency squawks.",
    "notMeaning": "A marker's shape or colour alone does not confirm an aircraft's identity or intentions.",
    "category": "Guide"
  },
  "title-Choose the receiver by its hardware and host; this selection is independent of ADS-B.": {
    "term": "Datalink receiver",
    "meaning": "Selects the physical SDR and the host that will decode ACARS or VDL2 messages.",
    "matters": "Choose an available VHF receiver independently of the receiver used for ADS-B tracking.",
    "notMeaning": "An ADS-B data feed does not provide VHF radio reception, and a busy SDR cannot tune to both bands at once.",
    "category": "Guide"
  },
  "mode-pager": {
    "term": "Pager",
    "meaning": "Decodes POCSAG and FLEX pager transmissions with a radio receiver.",
    "matters": "Choose a frequency and decoder to see messages heard nearby.",
    "notMeaning": "Missing messages do not show that a pager network is idle.",
    "category": "Mode"
  },
  "mode-sensor": {
    "term": "433 MHz sensors",
    "meaning": "Decodes supported sensor broadcasts using rtl_433.",
    "matters": "Shows readings from devices such as weather sensors.",
    "notMeaning": "Not every device on this band uses a supported protocol.",
    "category": "Mode"
  },
  "mode-rtlamr": {
    "term": "Utility meters",
    "meaning": "Receives supported utility-meter radio packets using rtlamr.",
    "matters": "Lets you inspect meter readings received by your antenna.",
    "notMeaning": "A decoded reading alone does not identify the property it serves.",
    "category": "Mode"
  },
  "mode-subghz": {
    "term": "SubGHz",
    "meaning": "Captures, inspects and replays radio signals using supported hardware.",
    "matters": "Useful for inspecting signals below one gigahertz.",
    "notMeaning": "A recording does not identify a protocol or grant permission to transmit.",
    "category": "Mode"
  },
  "mode-waterfall": {
    "term": "Waterfall",
    "meaning": "Plots received signal power across frequency over time.",
    "matters": "Helps find activity and tune the receiver.",
    "notMeaning": "A bright trace does not identify the transmitter or its message.",
    "category": "Mode"
  },
  "mode-morse": {
    "term": "Morse",
    "meaning": "Decodes Morse audio into text.",
    "matters": "Helps follow keyed signals when the receiver is tuned correctly.",
    "notMeaning": "Noise, speed and fading can produce incorrect characters.",
    "category": "Mode"
  },
  "mode-ook": {
    "term": "OOK decoder",
    "meaning": "Inspects on-off keyed pulses and prepares transmission commands.",
    "matters": "Pulse lengths help compare simple remote-control signals.",
    "notMeaning": "Similar pulses do not guarantee that a remote is compatible.",
    "category": "Mode"
  },
  "mode-adsb": {
    "term": "Aircraft",
    "meaning": "Maps aircraft reports decoded from ADS-B on 1090 MHz.",
    "matters": "Shows positions and flight information that receivers have heard.",
    "notMeaning": "It is not a complete or authoritative air-traffic picture.",
    "category": "Mode"
  },
  "mode-ais": {
    "term": "Vessels",
    "meaning": "Maps vessel reports received from the Automatic Identification System.",
    "matters": "Helps follow vessels that transmit AIS within reception range.",
    "notMeaning": "Missing reports do not mean that no vessel is present.",
    "category": "Mode"
  },
  "mode-aprs": {
    "term": "APRS",
    "meaning": "Decodes amateur packet-radio reports with position and message information.",
    "matters": "Shows stations and packets received by the selected source.",
    "notMeaning": "A reported position may be old or entered manually.",
    "category": "Mode"
  },
  "mode-gps": {
    "term": "GPS",
    "meaning": "Shows location information from a connected GPS receiver.",
    "matters": "A valid fix supplies an observer location for other tools.",
    "notMeaning": "A connected receiver does not necessarily have a valid position fix.",
    "category": "Mode"
  },
  "mode-radiosonde": {
    "term": "Radiosonde",
    "meaning": "Decodes weather-balloon telemetry using a radio receiver.",
    "matters": "Shows reported position, altitude and weather readings.",
    "notMeaning": "A predicted landing location is not a confirmed landing.",
    "category": "Mode"
  },
  "mode-satellite": {
    "term": "Satellites",
    "meaning": "Predicts passes and positions from orbital elements and your observer location.",
    "matters": "Helps plan when and where to point an antenna.",
    "notMeaning": "A predicted pass does not guarantee a usable transmission.",
    "category": "Mode"
  },
  "mode-iss": {
    "term": "ISS live",
    "meaning": "Shows the space station’s predicted orbit, passes and reception tools.",
    "matters": "Helps plan reception from your observer location.",
    "notMeaning": "Being above the horizon does not mean the ISS is transmitting.",
    "category": "Mode"
  },
  "mode-sstv": {
    "term": "ISS SSTV",
    "meaning": "Receives slow-scan television images on the ISS SSTV frequency.",
    "matters": "Builds images from received audio when SSTV is being transmitted.",
    "notMeaning": "A pass does not guarantee an SSTV broadcast.",
    "category": "Mode"
  },
  "mode-weathersat": {
    "term": "Weather satellites",
    "meaning": "Uses SatDump to receive supported weather-satellite imagery.",
    "matters": "A suitable pass, antenna and receiver can produce weather images.",
    "notMeaning": "A scheduled pass does not guarantee successful decoding.",
    "category": "Mode"
  },
  "mode-wefax": {
    "term": "Weather fax",
    "meaning": "Decodes weather-fax images carried on radio audio.",
    "matters": "Helps receive broadcast charts when tuned to the right station.",
    "notMeaning": "The received chart may be old or distorted by poor reception.",
    "category": "Mode"
  },
  "mode-sstv_general": {
    "term": "HF SSTV",
    "meaning": "Decodes slow-scan television images from radio audio.",
    "matters": "Lets you receive pictures on supported SSTV modes.",
    "notMeaning": "A decoded image does not authenticate its sender.",
    "category": "Mode"
  },
  "mode-spaceweather": {
    "term": "Space weather",
    "meaning": "Displays solar and geomagnetic information from data feeds.",
    "matters": "Conditions can help explain changes in radio propagation.",
    "notMeaning": "These indicators do not predict reception at one antenna precisely.",
    "category": "Mode"
  },
  "mode-meteor": {
    "term": "Meteor scatter",
    "meaning": "Monitors radio reflections associated with meteor scatter.",
    "matters": "Short signal bursts can help study changing propagation.",
    "notMeaning": "A single burst is not proof of a meteor.",
    "category": "Mode"
  },
  "mode-wifi": {
    "term": "WiFi",
    "meaning": "Scans wireless networks and clients using the available WiFi tools.",
    "matters": "Shows nearby observations, channels and security information.",
    "notMeaning": "An observed network or client is not evidence of malicious activity.",
    "category": "Mode"
  },
  "mode-bluetooth": {
    "term": "Bluetooth",
    "meaning": "Scans nearby Bluetooth advertisements and devices.",
    "matters": "Helps inspect device types and changes in nearby activity.",
    "notMeaning": "A device name or fingerprint does not establish ownership or intent.",
    "category": "Mode"
  },
  "mode-bt_locate": {
    "term": "Locate Bluetooth",
    "meaning": "Follows a selected device using repeated signal-strength observations.",
    "matters": "Changes in strength can help guide a physical search.",
    "notMeaning": "Signal strength is not a reliable distance measurement.",
    "category": "Mode"
  },
  "mode-wifi_locate": {
    "term": "Locate WiFi",
    "meaning": "Follows a selected WiFi signal using repeated strength observations.",
    "matters": "Helps compare reception as you move an antenna or receiver.",
    "notMeaning": "Reflections and obstacles prevent strength from being an exact range.",
    "category": "Mode"
  },
  "mode-drone": {
    "term": "Drone detection",
    "meaning": "Monitors supported drone-identification and radio observations.",
    "matters": "Can show reported drone information when broadcasts are received.",
    "notMeaning": "No detection does not prove that the airspace is clear.",
    "category": "Mode"
  },
  "mode-identity_management": {
    "term": "Device identities",
    "meaning": "Manages known device identities used by the inspection tools.",
    "matters": "Helps recognise observations you have already identified.",
    "notMeaning": "A stored identity does not guarantee that every matching observation is the same device.",
    "category": "Mode"
  },
  "mode-activity": {
    "term": "Activity",
    "meaning": "Reviews recorded signal and device activity.",
    "matters": "Helps compare observations over time.",
    "notMeaning": "An activity record is limited to what the tools captured.",
    "category": "Mode"
  },
  "mode-meshtastic": {
    "term": "Meshtastic",
    "meaning": "Connects to a Meshtastic radio to read nodes and exchange mesh messages.",
    "matters": "Lets you inspect and use the channels configured on that device.",
    "notMeaning": "A listed node may be stale or currently unreachable.",
    "category": "Mode"
  },
  "mode-meshcore": {
    "term": "MeshCore",
    "meaning": "Connects to a MeshCore radio for contacts and messages.",
    "matters": "Provides access to the mesh through the connected device.",
    "notMeaning": "A contact in the list does not guarantee a working route.",
    "category": "Mode"
  },
  "mode-spystations": {
    "term": "Spy stations",
    "meaning": "Lists known numbers-station and related shortwave frequencies.",
    "matters": "Offers tuning information for listening with a suitable receiver.",
    "notMeaning": "A listed frequency does not guarantee a current transmission.",
    "category": "Mode"
  },
  "mode-websdr": {
    "term": "WebSDR",
    "meaning": "Connects to remote receivers to listen to radio signals.",
    "matters": "Offers reception from locations beyond your own antenna.",
    "notMeaning": "Remote reception does not describe local signal conditions.",
    "category": "Mode"
  },
  "mode-tscm": {
    "term": "Counter-surveillance",
    "meaning": "Compares WiFi, Bluetooth and radio observations and flags patterns for review.",
    "matters": "Helps organise an inspection and compare against a baseline.",
    "notMeaning": "A flag is not proof of surveillance or hostile intent.",
    "category": "Mode"
  },
  "mode-tscmsurvey": {
    "term": "TSCM survey",
    "meaning": "Organises counter-surveillance surveys and their recorded findings.",
    "matters": "Helps keep inspection evidence and follow-up work together.",
    "notMeaning": "A survey cannot establish that a location is free of hidden devices.",
    "category": "Mode"
  },
  "mode-system": {
    "term": "System",
    "meaning": "Shows system health and tools for managing running processes.",
    "matters": "Helps diagnose resource use and decoder problems.",
    "notMeaning": "Healthy system readings do not guarantee good radio reception.",
    "category": "Mode"
  },
  "term-Gain": {
    "term": "Gain",
    "meaning": "Receiver amplification. Higher values amplify both signals and noise.",
    "matters": "Adjust it to decode weak signals without overloading the receiver.",
    "notMeaning": "Higher gain does not always improve reception.",
    "category": "Guide"
  },
  "term-Squelch": {
    "term": "Squelch",
    "meaning": "The signal threshold below which receiver audio is muted.",
    "matters": "Reduces noise between transmissions.",
    "notMeaning": "Muted audio does not prove the frequency is unused.",
    "category": "Guide"
  },
  "term-Volume": {
    "term": "Volume",
    "meaning": "Playback loudness for received audio.",
    "matters": "Changes what you hear without retuning the receiver.",
    "notMeaning": "It does not change radio gain or decoding sensitivity.",
    "category": "Guide"
  },
  "term-Latitude": {
    "term": "Latitude",
    "meaning": "Observer position north or south of the equator, in degrees.",
    "matters": "Used with longitude for distances, bearings and pass predictions.",
    "notMeaning": "It is the observer’s position, not a received transmitter position.",
    "category": "Guide"
  },
  "term-Longitude": {
    "term": "Longitude",
    "meaning": "Observer position east or west of Greenwich, in degrees.",
    "matters": "Used with latitude for distances, bearings and pass predictions.",
    "notMeaning": "It is not a measured radio bearing.",
    "category": "Guide"
  },
  "term-Altitude": {
    "term": "Altitude",
    "meaning": "Reported or predicted height; check the displayed units.",
    "matters": "Helps interpret aircraft, balloon or satellite position.",
    "notMeaning": "It does not by itself give height above local terrain.",
    "category": "Guide"
  },
  "term-Azimuth": {
    "term": "Azimuth",
    "meaning": "Compass direction measured clockwise from north.",
    "matters": "Helps point an antenna toward a predicted pass.",
    "notMeaning": "It does not measure signal strength.",
    "category": "Guide"
  },
  "term-Elevation": {
    "term": "Elevation",
    "meaning": "Angle above your local horizon, in degrees.",
    "matters": "Higher passes generally offer a clearer line of sight.",
    "notMeaning": "A positive angle does not guarantee reception.",
    "category": "Guide"
  },
  "term-Range": {
    "term": "Range",
    "meaning": "Distance shown using the current observer position and display units.",
    "matters": "Helps judge where a contact or pass is relative to you.",
    "notMeaning": "Map distance alone is not a reception guarantee.",
    "category": "Guide"
  },
  "term-Frequency": {
    "term": "Frequency",
    "meaning": "The radio frequency to which the receiver is tuned.",
    "matters": "It must match the transmission you want to receive.",
    "notMeaning": "Tuning alone does not select the right decoder or antenna.",
    "category": "Guide"
  },
  "term-RSSI": {
    "term": "RSSI",
    "meaning": "Received signal-strength indication from the scanning hardware.",
    "matters": "Helps compare observations made with the same setup.",
    "notMeaning": "It is not an exact distance or a calibrated comparison between receivers.",
    "category": "Guide"
  },
  "term-SNR": {
    "term": "SNR",
    "meaning": "Signal-to-noise ratio: how strongly a signal stands above the noise.",
    "matters": "A clearer signal is often easier to decode.",
    "notMeaning": "A strong signal does not establish who transmitted it.",
    "category": "Guide"
  },
  "term-Speed": {
    "term": "Speed",
    "meaning": "Speed reported in the received position data.",
    "matters": "Helps follow movement between position updates.",
    "notMeaning": "It may be stale and does not establish an intended route.",
    "category": "Guide"
  },
  "term-Heading": {
    "term": "Heading",
    "meaning": "Direction reported for a moving contact.",
    "matters": "Helps interpret its movement on the map.",
    "notMeaning": "It is not necessarily a planned destination.",
    "category": "Guide"
  },
  "term-Squawk": {
    "term": "Squawk",
    "meaning": "A four-digit transponder code reported by an aircraft.",
    "matters": "Some codes have special emergency or operational meanings.",
    "notMeaning": "A code alone does not explain the aircraft’s situation.",
    "category": "Guide"
  },
  "term-Messages": {
    "term": "Messages",
    "meaning": "Decoded messages counted or listed by this view.",
    "matters": "Helps check whether data is arriving.",
    "notMeaning": "A high count does not guarantee complete or error-free reception.",
    "category": "Guide"
  },
  "term-Packets": {
    "term": "Packets",
    "meaning": "Packets received or decoded by the active tool.",
    "matters": "Shows activity reaching the receiver.",
    "notMeaning": "Not every packet contains a position or readable text.",
    "category": "Guide"
  },
  "term-Signal": {
    "term": "Signal",
    "meaning": "Reception activity reported by the selected source.",
    "matters": "Helps tell whether reports are reaching the dashboard.",
    "notMeaning": "It is not a calibrated measurement of antenna performance.",
    "category": "Guide"
  },
  "term-Nodes": {
    "term": "Nodes",
    "meaning": "Devices known to the connected mesh radio.",
    "matters": "Shows available identities and their last reported details.",
    "notMeaning": "A known node is not necessarily online or reachable now.",
    "category": "Guide"
  },
  "term-Channel": {
    "term": "Channel",
    "meaning": "The selected radio or mesh channel.",
    "matters": "Controls which configured channel is used for this operation.",
    "notMeaning": "A channel name alone does not guarantee compatible settings or keys.",
    "category": "Guide"
  },
  "term-AOS azimuth": {
    "term": "AOS azimuth",
    "meaning": "Compass bearing where a satellite rises above the pass horizon.",
    "matters": "Helps choose the antenna’s starting direction.",
    "notMeaning": "It is a prediction based on orbital elements and observer location.",
    "category": "Guide"
  },
  "term-TCA azimuth": {
    "term": "TCA azimuth",
    "meaning": "Compass bearing at the satellite’s closest approach during the pass.",
    "matters": "Helps plan the middle of the antenna track.",
    "notMeaning": "Closest approach does not guarantee the best received signal.",
    "category": "Guide"
  },
  "term-LOS azimuth": {
    "term": "LOS azimuth",
    "meaning": "Compass bearing where the satellite leaves the pass horizon.",
    "matters": "Helps plan the end of the antenna track.",
    "notMeaning": "A predicted end time is not a measured loss of radio signal.",
    "category": "Guide"
  },
  "term-Bias-T": {
    "term": "Bias-T",
    "meaning": "Sends DC power through the antenna cable to compatible equipment.",
    "matters": "Can power an external amplifier that requires it.",
    "notMeaning": "Not all antennas or accessories can safely accept this power.",
    "category": "Guide"
  },
  "term-Reach": {
    "term": "Reach",
    "meaning": "Outline of the furthest received contact in each direction.",
    "matters": "Helps compare observed reception around the antenna.",
    "notMeaning": "It is historical reception, not a guaranteed coverage boundary.",
    "category": "Guide"
  },
  "term-Trails": {
    "term": "Trails",
    "meaning": "Draws paths from previously received positions.",
    "matters": "Makes recent movement easier to follow.",
    "notMeaning": "Gaps can be missing reception rather than a change of course.",
    "category": "Guide"
  },
  "term-Rings": {
    "term": "Rings",
    "meaning": "Distance circles centred on the observer location.",
    "matters": "Provides a scale for judging nearby contacts.",
    "notMeaning": "The circles do not measure receiver coverage.",
    "category": "Guide"
  },
  "term-Labels": {
    "term": "Labels",
    "meaning": "Shows identifying text beside map contacts when zoom allows.",
    "matters": "Helps recognise contacts without opening each one.",
    "notMeaning": "Hiding labels does not stop reception.",
    "category": "Guide"
  },
  "term-Source": {
    "term": "Source",
    "meaning": "The local receiver or remote agent supplying this view.",
    "matters": "Check it before interpreting data or starting a decoder.",
    "notMeaning": "An agent’s reception conditions may differ from your local antenna.",
    "category": "Guide"
  },
  "term-SDR device": {
    "term": "SDR device",
    "meaning": "The software-defined radio assigned to this decoder.",
    "matters": "Different modes may need separate receivers or frequency bands.",
    "notMeaning": "Selecting a device does not start reception by itself.",
    "category": "Guide"
  },
  "term-GPS connected via gpsd": {
    "term": "GPS connected via gpsd",
    "meaning": "The application is receiving GPS information through gpsd.",
    "matters": "Can supply the observer position for map calculations.",
    "notMeaning": "A connection alone does not establish fix accuracy.",
    "category": "Guide"
  },
  "term-Signal quality (messages/sec)": {
    "term": "Signal quality (messages/sec)",
    "meaning": "Number of AIS messages arriving per second.",
    "matters": "Helps check whether the selected source is delivering reports.",
    "notMeaning": "Message rate is not a direct measurement of RF signal strength.",
    "category": "Guide"
  },
  "term-Signal quality (messages/errors)": {
    "term": "Signal quality (messages/errors)",
    "meaning": "Message and error counts from the ADS-B decoder.",
    "matters": "Helps compare decoding activity with the same setup.",
    "notMeaning": "It is not calibrated radio signal strength.",
    "category": "Guide"
  },
  "term-Enable Bias-T power for external LNA/preamp": {
    "term": "Enable Bias-T power for external LNA/preamp",
    "meaning": "Supplies DC power on the antenna cable for a compatible amplifier.",
    "matters": "Use only when your connected equipment needs and supports this power.",
    "notMeaning": "It is not safe for every antenna or accessory.",
    "category": "Guide"
  },
  "term-Outline of the furthest contact heard in each direction": {
    "term": "Outline of the furthest contact heard in each direction",
    "meaning": "Draws a boundary from the furthest contacts received around this location.",
    "matters": "Useful for comparing observed reception over time.",
    "notMeaning": "The outline is not guaranteed coverage.",
    "category": "Guide"
  },
  "term-Forget the reception outline for this location": {
    "term": "Forget the reception outline for this location",
    "meaning": "Clears the stored reception boundary for this observer location.",
    "matters": "Lets a new antenna setup build a fresh comparison.",
    "notMeaning": "It does not erase every contact or stop the decoder.",
    "category": "Guide"
  },
  "term-Range rings distance": {
    "term": "Range rings distance",
    "meaning": "Sets the map’s distance scale for the observer-centred rings.",
    "matters": "Helps compare contact distances from the configured observer.",
    "notMeaning": "This display scale does not change receiver sensitivity.",
    "category": "Guide"
  },
  "term-Select signal source": {
    "term": "Select signal source",
    "meaning": "Chooses the local machine or a remote agent as the data source.",
    "matters": "Data and decoder controls apply to the selected source.",
    "notMeaning": "Choosing a source does not move your antenna.",
    "category": "Guide"
  },
  "term-Drop aircraft not heard from for this long": {
    "term": "Drop aircraft not heard from for this long",
    "meaning": "Removes aircraft from this live view after the selected silence interval.",
    "matters": "Keeps stale positions from lingering on the map.",
    "notMeaning": "Disappearance does not mean the aircraft has landed.",
    "category": "Guide"
  },
  "term-SDR gain in dB (0 = auto)": {
    "term": "SDR gain in dB (0 = auto)",
    "meaning": "Sets ADS-B receiver gain in decibels; this control uses zero for automatic gain.",
    "matters": "Balance weak-signal reception against overload.",
    "notMeaning": "More gain is not always better.",
    "category": "Guide"
  },
  "term-Distress alerts": {
    "term": "Distress alerts",
    "meaning": "Counts received DSC distress alerts.",
    "matters": "Draws attention to distress messages heard by the decoder.",
    "notMeaning": "A decoded alert alone is not independent confirmation of an emergency.",
    "category": "Guide"
  },
  "term-Urgency alerts": {
    "term": "Urgency alerts",
    "meaning": "Counts received DSC urgency messages.",
    "matters": "Separates urgent messages from ordinary vessel reports.",
    "notMeaning": "It is not an independently verified incident count.",
    "category": "Guide"
  },
  "term-direwolf": {
    "term": "direwolf",
    "meaning": "Dire Wolf is a software packet-radio modem used by APRS reception.",
    "matters": "The indicator helps check whether this decoder is available.",
    "notMeaning": "Tool availability does not mean a packet was received.",
    "category": "Guide"
  },
  "term-multimon-ng": {
    "term": "multimon-ng",
    "meaning": "A decoder for several radio data formats.",
    "matters": "Used by reception tools to turn demodulated audio into messages.",
    "notMeaning": "Installed software does not guarantee a supported signal is present.",
    "category": "Guide"
  },
  "title-Select observer location": {
    "term": "Select observer location",
    "meaning": "Chooses the observer position used by maps and pass calculations.",
    "matters": "Distances, bearings and pass times depend on this location.",
    "notMeaning": "It does not change where a remote receiver is physically located.",
    "category": "Guide"
  },
  "title-Refresh satellite list": {
    "term": "Refresh satellite list",
    "meaning": "Reloads satellite or pass information for this view.",
    "matters": "Use after changing tracked objects or observer settings.",
    "notMeaning": "Refreshing predictions does not start a radio capture.",
    "category": "Guide"
  },
  "title-Switch to Weather Satellite mode for this pass": {
    "term": "Switch to Weather Satellite mode for this pass",
    "meaning": "Opens Weather Satellite mode with information for the selected pass.",
    "matters": "Helps prepare the appropriate weather-satellite capture.",
    "notMeaning": "A handoff does not guarantee that reception will succeed.",
    "category": "Guide"
  },
  "title-AOS azimuth": {
    "term": "AOS azimuth",
    "meaning": "Compass bearing where a satellite rises above the pass horizon.",
    "matters": "Helps choose the antenna’s starting direction.",
    "notMeaning": "It is a prediction based on orbital elements and observer location.",
    "category": "Guide"
  },
  "title-TCA azimuth": {
    "term": "TCA azimuth",
    "meaning": "Compass bearing at the satellite’s closest approach during the pass.",
    "matters": "Helps plan the middle of the antenna track.",
    "notMeaning": "Closest approach does not guarantee the best received signal.",
    "category": "Guide"
  },
  "title-LOS azimuth": {
    "term": "LOS azimuth",
    "meaning": "Compass bearing where the satellite leaves the pass horizon.",
    "matters": "Helps plan the end of the antenna track.",
    "notMeaning": "A predicted end time is not a measured loss of radio signal.",
    "category": "Guide"
  },
  "title-Remove tracked satellite": {
    "term": "Remove tracked satellite",
    "meaning": "Remove tracked satellite",
    "matters": "Use this when the selected record or view is no longer needed.",
    "notMeaning": "Check the selected item before using a removal control.",
    "category": "Guide"
  },
  "title-Settings": {
    "term": "Settings",
    "meaning": "Settings.",
    "matters": "Opens the named view or changes the named interface preference.",
    "notMeaning": "This control is separate from the radio decoder settings.",
    "category": "Guide"
  },
  "title-Collapse sidebar": {
    "term": "Collapse sidebar",
    "meaning": "Collapse sidebar.",
    "matters": "Changes which controls or details are visible without leaving the current page.",
    "notMeaning": "Opening or hiding a panel does not start or stop reception.",
    "category": "Guide"
  },
  "title-Agent status": {
    "term": "Agent status",
    "meaning": "Agent status",
    "matters": "Check this before starting reception or interpreting received data.",
    "notMeaning": "Availability of a source does not guarantee reception.",
    "category": "Guide"
  },
  "title-Expand sidebar": {
    "term": "Expand sidebar",
    "meaning": "Expand sidebar.",
    "matters": "Changes which controls or details are visible without leaving the current page.",
    "notMeaning": "Opening or hiding a panel does not start or stop reception.",
    "category": "Guide"
  },
  "title-Total Messages": {
    "term": "Total Messages",
    "meaning": "Count of decoded messages in this view.",
    "matters": "Helps check whether the decoder is producing output.",
    "notMeaning": "It is not a count of every transmission on the frequency.",
    "category": "Guide"
  },
  "title-POCSAG Messages": {
    "term": "POCSAG Messages",
    "meaning": "Messages decoded using the POCSAG pager format.",
    "matters": "Separates this format from FLEX pager traffic.",
    "notMeaning": "A successful decode does not authenticate the sender.",
    "category": "Guide"
  },
  "title-FLEX Messages": {
    "term": "FLEX Messages",
    "meaning": "Messages decoded using the FLEX pager format.",
    "matters": "Separates this format from POCSAG pager traffic.",
    "notMeaning": "Poor reception can leave messages missing or incomplete.",
    "category": "Guide"
  },
  "title-Unique Sensors": {
    "term": "Unique Sensors",
    "meaning": "Distinct sensor identities observed in decoded packets.",
    "matters": "Helps distinguish devices from repeated readings.",
    "notMeaning": "An identity is not a confirmed physical location or owner.",
    "category": "Guide"
  },
  "title-Device Types": {
    "term": "Device Types",
    "meaning": "Device Types",
    "matters": "Check this before starting reception or interpreting received data.",
    "notMeaning": "Availability of a source does not guarantee reception.",
    "category": "Guide"
  },
  "title-Access Points": {
    "term": "Access Points",
    "meaning": "WiFi access points observed by the scanner.",
    "matters": "Summarises nearby network advertisements.",
    "notMeaning": "It is not a count of all networks in the area.",
    "category": "Guide"
  },
  "title-Connected Clients": {
    "term": "Connected Clients",
    "meaning": "Connected Clients",
    "matters": "Adds context to an observation that may need your attention.",
    "notMeaning": "A label or alert alone does not establish identity, intent or danger.",
    "category": "Guide"
  },
  "title-Captured Handshakes": {
    "term": "Captured Handshakes",
    "meaning": "WiFi authentication exchanges saved by the capture tools.",
    "matters": "Shows which captures are available for inspection.",
    "notMeaning": "A handshake is not a recovered password.",
    "category": "Guide"
  },
  "title-Click: Drone details": {
    "term": "Click: Drone details",
    "meaning": "Click: Drone details",
    "matters": "Open this item to inspect its recorded details.",
    "notMeaning": "Recorded details may be incomplete or out of date.",
    "category": "Guide"
  },
  "title-Click: Rogue AP details": {
    "term": "Click: Rogue AP details",
    "meaning": "Click: Rogue AP details",
    "matters": "Open this item to inspect its recorded details.",
    "notMeaning": "Recorded details may be incomplete or out of date.",
    "category": "Guide"
  },
  "title-Upcoming Passes": {
    "term": "Upcoming Passes",
    "meaning": "Predicted satellite passes for the configured observer.",
    "matters": "Helps schedule reception while a satellite is above the horizon.",
    "notMeaning": "A prediction is not confirmation of a usable signal.",
    "category": "Guide"
  },
  "title-Capture this network's WPA handshake (monitor mode required)": {
    "term": "Capture this network's WPA handshake (monitor mode required)",
    "meaning": "Capture this network's WPA handshake (monitor mode required)",
    "matters": "Open this item to inspect its recorded details.",
    "notMeaning": "Recorded details may be incomplete or out of date.",
    "category": "Guide"
  },
  "title-Locate this network": {
    "term": "Locate this network",
    "meaning": "Locate this network",
    "matters": "Open this item to inspect its recorded details.",
    "notMeaning": "Recorded details may be incomplete or out of date.",
    "category": "Guide"
  },
  "title-Send deauth to this network — authorized testing only": {
    "term": "Send deauth to this network — authorized testing only",
    "meaning": "Send deauth to this network — authorized testing only",
    "matters": "Open this item to inspect its recorded details.",
    "notMeaning": "Recorded details may be incomplete or out of date.",
    "category": "Guide"
  },
  "title-Locate this AP": {
    "term": "Locate this AP",
    "meaning": "Locate this AP",
    "matters": "Open this item to inspect its recorded details.",
    "notMeaning": "Recorded details may be incomplete or out of date.",
    "category": "Guide"
  },
  "title-Locate this device": {
    "term": "Locate this device",
    "meaning": "Locate this device",
    "matters": "Check this before starting reception or interpreting received data.",
    "notMeaning": "Availability of a source does not guarantee reception.",
    "category": "Guide"
  },
  "title-WiFi Capability": {
    "term": "WiFi Capability",
    "meaning": "Indicates WiFi support or WiFi observations for this item.",
    "matters": "Helps identify which radio layer contributes to the view.",
    "notMeaning": "A WiFi observation does not establish ownership or intent.",
    "category": "Guide"
  },
  "title-Bluetooth Capability": {
    "term": "Bluetooth Capability",
    "meaning": "Indicates Bluetooth support or Bluetooth observations for this item.",
    "matters": "Helps identify which radio layer contributes to the view.",
    "notMeaning": "A Bluetooth fingerprint does not authenticate a device.",
    "category": "Guide"
  },
  "title-RF/SDR Capability": {
    "term": "RF/SDR Capability",
    "meaning": "RF/SDR Capability",
    "matters": "Check this before starting reception or interpreting received data.",
    "notMeaning": "Availability of a source does not guarantee reception.",
    "category": "Guide"
  },
  "title-Privilege Level": {
    "term": "Privilege Level",
    "meaning": "Shows the privilege information reported by the system check.",
    "matters": "Some radio tools need elevated permissions to access hardware.",
    "notMeaning": "Privileges alone do not make a decoder available or configured.",
    "category": "Guide"
  },
  "title-Click to view high interest devices": {
    "term": "Click to view high interest devices",
    "meaning": "Click to view high interest devices",
    "matters": "Check this before starting reception or interpreting received data.",
    "notMeaning": "Availability of a source does not guarantee reception.",
    "category": "Guide"
  },
  "title-Click to view devices needing review": {
    "term": "Click to view devices needing review",
    "meaning": "Click to view devices needing review",
    "matters": "Check this before starting reception or interpreting received data.",
    "notMeaning": "Availability of a source does not guarantee reception.",
    "category": "Guide"
  },
  "title-Click to view informational devices": {
    "term": "Click to view informational devices",
    "meaning": "Click to view informational devices",
    "matters": "Check this before starting reception or interpreting received data.",
    "notMeaning": "Availability of a source does not guarantee reception.",
    "category": "Guide"
  },
  "title-Click to view correlations": {
    "term": "Click to view correlations",
    "meaning": "Opens observations that the tool has linked together.",
    "matters": "Helps compare evidence across observations.",
    "notMeaning": "Correlation does not prove a shared physical device or owner.",
    "category": "Guide"
  },
  "title-Click to view identity clusters": {
    "term": "Click to view identity clusters",
    "meaning": "Opens observations grouped by the identity-matching logic.",
    "matters": "Helps review devices despite changing identifiers.",
    "notMeaning": "A cluster is a heuristic grouping, not an authenticated identity.",
    "category": "Guide"
  },
  "title-Live burst detector": {
    "term": "Live burst detector",
    "meaning": "Detects short periods of radio activity in the live spectrum.",
    "matters": "Helps find intermittent signals for closer inspection.",
    "notMeaning": "A burst does not identify a protocol, transmitter or intent.",
    "category": "Guide"
  },
  "title-Back to hub": {
    "term": "Back to hub",
    "meaning": "Back to hub.",
    "matters": "Opens the named view or changes the named interface preference.",
    "notMeaning": "This control is separate from the radio decoder settings.",
    "category": "Guide"
  },
  "title-Latitude": {
    "term": "Latitude",
    "meaning": "Observer position north or south of the equator, in degrees.",
    "matters": "Used with longitude for distances, bearings and pass predictions.",
    "notMeaning": "It is the observer’s position, not a received transmitter position.",
    "category": "Guide"
  },
  "title-Longitude": {
    "term": "Longitude",
    "meaning": "Observer position east or west of Greenwich, in degrees.",
    "matters": "Used with latitude for distances, bearings and pass predictions.",
    "notMeaning": "It is not a measured radio bearing.",
    "category": "Guide"
  },
  "title-Use GPS location": {
    "term": "Use GPS location",
    "meaning": "Chooses the observer position used by maps and pass calculations.",
    "matters": "Distances, bearings and pass times depend on this location.",
    "notMeaning": "It does not change where a remote receiver is physically located.",
    "category": "Guide"
  },
  "title-Update satellite orbital data from CelesTrak": {
    "term": "Update satellite orbital data from CelesTrak",
    "meaning": "Requests updated orbital elements from CelesTrak.",
    "matters": "Fresh elements improve pass and position predictions.",
    "notMeaning": "Updated elements do not confirm that a satellite is transmitting.",
    "category": "Guide"
  },
  "title-Delete all images": {
    "term": "Delete all images",
    "meaning": "Delete all images",
    "matters": "Use this when the selected record or view is no longer needed.",
    "notMeaning": "Check the selected item before using a removal control.",
    "category": "Guide"
  },
  "title-Auto-capture passes": {
    "term": "Auto-capture passes",
    "meaning": "Enables the mode’s automatic capture scheduling.",
    "matters": "Lets configured reception run for scheduled opportunities.",
    "notMeaning": "Success still depends on hardware, configuration and a usable signal.",
    "category": "Guide"
  },
  "title-Copy log to clipboard": {
    "term": "Copy log to clipboard",
    "meaning": "Copy log to clipboard",
    "matters": "Lets you keep or reuse the information currently offered by this view.",
    "notMeaning": "The output is limited to the information captured by the application.",
    "category": "Guide"
  },
  "title-Clear console": {
    "term": "Clear console",
    "meaning": "Clear console",
    "matters": "Use this when the selected record or view is no longer needed.",
    "notMeaning": "Check the selected item before using a removal control.",
    "category": "Guide"
  },
  "title-Toggle console": {
    "term": "Toggle console",
    "meaning": "Toggle console.",
    "matters": "Changes which controls or details are visible without leaving the current page.",
    "notMeaning": "Opening or hiding a panel does not start or stop reception.",
    "category": "Guide"
  },
  "title-Refresh pass predictions": {
    "term": "Refresh pass predictions",
    "meaning": "Reloads satellite or pass information for this view.",
    "matters": "Use after changing tracked objects or observer settings.",
    "notMeaning": "Refreshing predictions does not start a radio capture.",
    "category": "Guide"
  },
  "title-Auto-capture broadcasts": {
    "term": "Auto-capture broadcasts",
    "meaning": "Enables the mode’s automatic capture scheduling.",
    "matters": "Lets configured reception run for scheduled opportunities.",
    "notMeaning": "Success still depends on hardware, configuration and a usable signal.",
    "category": "Guide"
  },
  "title-Step down ×10": {
    "term": "Step down ×10",
    "meaning": "Changes tuning by ten times the current step size.",
    "matters": "Moves more quickly across frequencies.",
    "notMeaning": "It does not automatically select an active signal.",
    "category": "Guide"
  },
  "title-Step down": {
    "term": "Step down",
    "meaning": "Changes tuning by the current step size.",
    "matters": "Lets you adjust the tuned frequency precisely.",
    "notMeaning": "A tuning step does not guarantee a decodable signal.",
    "category": "Guide"
  },
  "title-Step up": {
    "term": "Step up",
    "meaning": "Changes tuning by the current step size.",
    "matters": "Lets you adjust the tuned frequency precisely.",
    "notMeaning": "A tuning step does not guarantee a decodable signal.",
    "category": "Guide"
  },
  "title-Step up ×10": {
    "term": "Step up ×10",
    "meaning": "Changes tuning by ten times the current step size.",
    "matters": "Moves more quickly across frequencies.",
    "notMeaning": "It does not automatically select an active signal.",
    "category": "Guide"
  },
  "title-Zoom out (wider span)": {
    "term": "Zoom out (wider span)",
    "meaning": "Changes the frequency span shown by the spectrum.",
    "matters": "Trade a wider overview for more detail around the tuned frequency.",
    "notMeaning": "A visual span change does not identify signals for you.",
    "category": "Guide"
  },
  "title-Zoom in (narrower span)": {
    "term": "Zoom in (narrower span)",
    "meaning": "Changes the frequency span shown by the spectrum.",
    "matters": "Trade a wider overview for more detail around the tuned frequency.",
    "notMeaning": "A visual span change does not identify signals for you.",
    "category": "Guide"
  },
  "title-Auto-detect best bit order from printable character count": {
    "term": "Auto-detect best bit order from printable character count",
    "meaning": "Chooses the bit order that yields more printable characters.",
    "matters": "Helps inspect unfamiliar captured data.",
    "notMeaning": "Printable output is a heuristic, not proof that the decoding is correct.",
    "category": "Guide"
  },
  "title-Export Device Intelligence": {
    "term": "Export Device Intelligence",
    "meaning": "Export Device Intelligence",
    "matters": "Lets you keep or reuse the information currently offered by this view.",
    "notMeaning": "The output is limited to the information captured by the application.",
    "category": "Guide"
  },
  "title-Select signal source": {
    "term": "Select signal source",
    "meaning": "Chooses the local machine or a remote agent as the data source.",
    "matters": "Data and decoder controls apply to the selected source.",
    "notMeaning": "Choosing a source does not move your antenna.",
    "category": "Guide"
  },
  "title-Show aircraft from all agents on map": {
    "term": "Show aircraft from all agents on map",
    "meaning": "Show aircraft from all agents on map",
    "matters": "Check this before starting reception or interpreting received data.",
    "notMeaning": "Availability of a source does not guarantee reception.",
    "category": "Guide"
  },
  "title-Data source (Local or Agent name)": {
    "term": "Data source (Local or Agent name)",
    "meaning": "Data source (Local or Agent name)",
    "matters": "Check this before starting reception or interpreting received data.",
    "notMeaning": "Availability of a source does not guarantee reception.",
    "category": "Guide"
  },
  "title-Signal quality (messages/errors)": {
    "term": "Signal quality (messages/errors)",
    "meaning": "Message and error counts from the ADS-B decoder.",
    "matters": "Helps compare decoding activity with the same setup.",
    "notMeaning": "It is not calibrated radio signal strength.",
    "category": "Guide"
  },
  "title-Squawk Code Reference": {
    "term": "Squawk Code Reference",
    "meaning": "Opens an explanation of aircraft transponder codes.",
    "matters": "Helps interpret codes with special operational meanings.",
    "notMeaning": "The code alone does not explain an aircraft’s circumstances.",
    "category": "Guide"
  },
  "title-Lookup selected aircraft on FlightAware": {
    "term": "Lookup selected aircraft on FlightAware",
    "meaning": "Opens a FlightAware lookup for the selected aircraft.",
    "matters": "Offers external flight context beyond local reception.",
    "notMeaning": "External records may be incomplete or differ from current reception.",
    "category": "Guide"
  },
  "title-Tune the airband receiver to the nearest airport's ATC frequency for the selected aircraft": {
    "term": "Tune the airband receiver to the nearest airport's ATC frequency for the selected aircraft",
    "meaning": "Tune the airband receiver to the nearest airport's ATC frequency for the selected aircraft",
    "matters": "Check this before starting reception or interpreting received data.",
    "notMeaning": "Availability of a source does not guarantee reception.",
    "category": "Guide"
  },
  "title-Open a pop-out instrument panel for the selected aircraft": {
    "term": "Open a pop-out instrument panel for the selected aircraft",
    "meaning": "Opens a separate instrument view for the selected aircraft.",
    "matters": "Keeps reported flight measurements together.",
    "notMeaning": "The instruments display received data, not certified cockpit readings.",
    "category": "Guide"
  },
  "title-Generate Session Report": {
    "term": "Generate Session Report",
    "meaning": "Generate Session Report",
    "matters": "Lets you keep or reuse the information currently offered by this view.",
    "notMeaning": "The output is limited to the information captured by the application.",
    "category": "Guide"
  },
  "title-Open History Reporting": {
    "term": "Open History Reporting",
    "meaning": "Open History Reporting",
    "matters": "Lets you keep or reuse the information currently offered by this view.",
    "notMeaning": "The output is limited to the information captured by the application.",
    "category": "Guide"
  },
  "title-1090 MHz Antenna Guide": {
    "term": "1090 MHz Antenna Guide",
    "meaning": "Opens guidance for an ADS-B antenna on 1090 MHz.",
    "matters": "A suitable antenna improves the chance of decoding ADS-B.",
    "notMeaning": "Antenna guidance cannot guarantee a particular reception range.",
    "category": "Guide"
  },
  "title-Where ACARS runs: with ADS-B, on this machine, or on an agent": {
    "term": "Where ACARS runs: with ADS-B, on this machine, or on an agent",
    "meaning": "Where ACARS runs: with ADS-B, on this machine, or on an agent",
    "matters": "Check this before starting reception or interpreting received data.",
    "notMeaning": "Availability of a source does not guarantee reception.",
    "category": "Guide"
  },
  "title-Clear messages": {
    "term": "Clear messages",
    "meaning": "Clear messages",
    "matters": "Use this when the selected record or view is no longer needed.",
    "notMeaning": "Check the selected item before using a removal control.",
    "category": "Guide"
  },
  "title-Toggle ACARS Panel": {
    "term": "Toggle ACARS Panel",
    "meaning": "Toggle ACARS Panel.",
    "matters": "Changes which controls or details are visible without leaving the current page.",
    "notMeaning": "Opening or hiding a panel does not start or stop reception.",
    "category": "Guide"
  },
  "title-Export VDL2 to CSV": {
    "term": "Export VDL2 to CSV",
    "meaning": "Export VDL2 to CSV",
    "matters": "Lets you keep or reuse the information currently offered by this view.",
    "notMeaning": "The output is limited to the information captured by the application.",
    "category": "Guide"
  },
  "title-Where VDL2 runs: with ADS-B, on this machine, or on an agent": {
    "term": "Where VDL2 runs: with ADS-B, on this machine, or on an agent",
    "meaning": "Where VDL2 runs: with ADS-B, on this machine, or on an agent",
    "matters": "Check this before starting reception or interpreting received data.",
    "notMeaning": "Availability of a source does not guarantee reception.",
    "category": "Guide"
  },
  "title-Toggle VDL2 Panel": {
    "term": "Toggle VDL2 Panel",
    "meaning": "Toggle VDL2 Panel.",
    "matters": "Changes which controls or details are visible without leaving the current page.",
    "notMeaning": "Opening or hiding a panel does not start or stop reception.",
    "category": "Guide"
  },
  "title-Show aircraft trails": {
    "term": "Show aircraft trails",
    "meaning": "Show aircraft trails",
    "matters": "Changes which information is drawn or listed in this view.",
    "notMeaning": "A display choice does not change what the receiver can hear.",
    "category": "Guide"
  },
  "title-Show range rings": {
    "term": "Show range rings",
    "meaning": "Show range rings",
    "matters": "Changes which information is drawn or listed in this view.",
    "notMeaning": "A display choice does not change what the receiver can hear.",
    "category": "Guide"
  },
  "title-Callsign and flight level beside each aircraft, when zoomed in": {
    "term": "Callsign and flight level beside each aircraft, when zoomed in",
    "meaning": "Shows contact labels beside markers when map zoom allows.",
    "matters": "Helps identify contacts without opening each one.",
    "notMeaning": "Hiding labels does not stop receiving reports.",
    "category": "Guide"
  },
  "title-Outline of the furthest contact heard in each direction": {
    "term": "Outline of the furthest contact heard in each direction",
    "meaning": "Draws a boundary from the furthest contacts received around this location.",
    "matters": "Useful for comparing observed reception over time.",
    "notMeaning": "The outline is not guaranteed coverage.",
    "category": "Guide"
  },
  "title-Forget the reception outline for this location": {
    "term": "Forget the reception outline for this location",
    "meaning": "Clears the stored reception boundary for this observer location.",
    "matters": "Lets a new antenna setup build a fresh comparison.",
    "notMeaning": "It does not erase every contact or stop the decoder.",
    "category": "Guide"
  },
  "title-Audio alerts for military/emergency": {
    "term": "Audio alerts for military/emergency",
    "meaning": "Audio alerts for military/emergency",
    "matters": "Adds context to an observation that may need your attention.",
    "notMeaning": "A label or alert alone does not establish identity, intent or danger.",
    "category": "Guide"
  },
  "title-Sound when new aircraft detected": {
    "term": "Sound when new aircraft detected",
    "meaning": "Plays a sound when a new aircraft is detected.",
    "matters": "Lets you notice arrivals without watching the map.",
    "notMeaning": "A new contact is not necessarily a new arrival in the area.",
    "category": "Guide"
  },
  "title-Filter aircraft": {
    "term": "Filter aircraft",
    "meaning": "Filter aircraft",
    "matters": "Changes which information is drawn or listed in this view.",
    "notMeaning": "A display choice does not change what the receiver can hear.",
    "category": "Guide"
  },
  "title-Manage Watchlist": {
    "term": "Manage Watchlist",
    "meaning": "Opens the aircraft watchlist editor.",
    "matters": "Choose identities that should be highlighted by the view.",
    "notMeaning": "A match is not evidence of unusual activity.",
    "category": "Guide"
  },
  "title-Range rings distance": {
    "term": "Range rings distance",
    "meaning": "Sets the map’s distance scale for the observer-centred rings.",
    "matters": "Helps compare contact distances from the configured observer.",
    "notMeaning": "This display scale does not change receiver sensitivity.",
    "category": "Guide"
  },
  "title-Only show aircraft within the range distance above (useful for busy remote/aggregated feeds)": {
    "term": "Only show aircraft within the range distance above (useful for busy remote/aggregated feeds)",
    "meaning": "Only show aircraft within the range distance above (useful for busy remote/aggregated feeds)",
    "matters": "Changes which information is drawn or listed in this view.",
    "notMeaning": "A display choice does not change what the receiver can hear.",
    "category": "Guide"
  },
  "title-Drop aircraft not heard from for this long": {
    "term": "Drop aircraft not heard from for this long",
    "meaning": "Removes aircraft from this live view after the selected silence interval.",
    "matters": "Keeps stale positions from lingering on the map.",
    "notMeaning": "Disappearance does not mean the aircraft has landed.",
    "category": "Guide"
  },
  "title-GPS connected via gpsd": {
    "term": "GPS connected via gpsd",
    "meaning": "The application is receiving GPS information through gpsd.",
    "matters": "Can supply the observer position for map calculations.",
    "notMeaning": "A connection alone does not establish fix accuracy.",
    "category": "Guide"
  },
  "title-Remote receiver health": {
    "term": "Remote receiver health",
    "meaning": "Whether the chosen remote ADS-B feed accepted a TCP connection at its last check, about once a minute.",
    "matters": "Shows at a glance whether the shared receiver you picked is reachable before or while you track.",
    "notMeaning": "Online does not prove the feed is sending aircraft. Remote coverage does not describe reception at your own antenna.",
    "category": "Guide"
  },
  "title-SDR device for ADS-B (1090 MHz)": {
    "term": "SDR device for ADS-B (1090 MHz)",
    "meaning": "SDR device for ADS-B (1090 MHz)",
    "matters": "Check this before starting reception or interpreting received data.",
    "notMeaning": "Availability of a source does not guarantee reception.",
    "category": "Guide"
  },
  "title-SDR gain in dB (0 = auto)": {
    "term": "SDR gain in dB (0 = auto)",
    "meaning": "Sets ADS-B receiver gain in decibels; this control uses zero for automatic gain.",
    "matters": "Balance weak-signal reception against overload.",
    "notMeaning": "More gain is not always better.",
    "category": "Guide"
  },
  "title-SDR gain in dB": {
    "term": "SDR gain in dB",
    "meaning": "SDR gain in dB",
    "matters": "Check this before starting reception or interpreting received data.",
    "notMeaning": "Availability of a source does not guarantee reception.",
    "category": "Guide"
  },
  "title-Enable Bias-T power for external LNA/preamp": {
    "term": "Enable Bias-T power for external LNA/preamp",
    "meaning": "Supplies DC power on the antenna cable for a compatible amplifier.",
    "matters": "Use only when your connected equipment needs and supports this power.",
    "notMeaning": "It is not safe for every antenna or accessory.",
    "category": "Guide"
  },
  "title-Airband receiver": {
    "term": "Airband receiver",
    "meaning": "Opens controls for listening to airband voice radio.",
    "matters": "Use a suitable receiver and frequency to hear nearby transmissions.",
    "notMeaning": "ADS-B position reception does not include voice audio.",
    "category": "Guide"
  },
  "title-Airband frequency": {
    "term": "Airband frequency",
    "meaning": "Airband frequency",
    "matters": "The setting must suit the signal and hardware you are using.",
    "notMeaning": "A setting alone does not confirm that a signal can be decoded.",
    "category": "Guide"
  },
  "title-Channel spacing": {
    "term": "Channel spacing",
    "meaning": "Channel spacing",
    "matters": "The setting must suit the signal and hardware you are using.",
    "notMeaning": "A setting alone does not confirm that a signal can be decoded.",
    "category": "Guide"
  },
  "title-SDR for airband": {
    "term": "SDR for airband",
    "meaning": "SDR for airband",
    "matters": "Check this before starting reception or interpreting received data.",
    "notMeaning": "Availability of a source does not guarantee reception.",
    "category": "Guide"
  },
  "title-Squelch": {
    "term": "Squelch",
    "meaning": "The signal threshold below which receiver audio is muted.",
    "matters": "Reduces noise between transmissions.",
    "notMeaning": "Muted audio does not prove the frequency is unused.",
    "category": "Guide"
  },
  "title-Volume": {
    "term": "Volume",
    "meaning": "Playback loudness for received audio.",
    "matters": "Changes what you hear without retuning the receiver.",
    "notMeaning": "It does not change radio gain or decoding sensitivity.",
    "category": "Guide"
  },
  "title-Remove": {
    "term": "Remove",
    "meaning": "Remove",
    "matters": "Use this when the selected record or view is no longer needed.",
    "notMeaning": "Check the selected item before using a removal control.",
    "category": "Guide"
  },
  "title-Has ACARS messages": {
    "term": "Has ACARS messages",
    "meaning": "This aircraft has associated decoded ACARS messages.",
    "matters": "Open the datalink view for additional received information.",
    "notMeaning": "The association does not guarantee that every message is current.",
    "category": "Guide"
  },
  "title-Click for squawk info": {
    "term": "Click for squawk info",
    "meaning": "Opens an explanation of aircraft transponder codes.",
    "matters": "Helps interpret codes with special operational meanings.",
    "notMeaning": "The code alone does not explain an aircraft’s circumstances.",
    "category": "Guide"
  },
  "title-Clear datalink messages": {
    "term": "Clear datalink messages",
    "meaning": "Clear datalink messages",
    "matters": "Use this when the selected record or view is no longer needed.",
    "notMeaning": "Check the selected item before using a removal control.",
    "category": "Guide"
  },
  "title-Tracked on map": {
    "term": "Tracked on map",
    "meaning": "This record has position information available to the map.",
    "matters": "Lets you connect a message or device with its displayed location.",
    "notMeaning": "The position may be old or self-reported.",
    "category": "Guide"
  },
  "title-Close": {
    "term": "Close",
    "meaning": "Close.",
    "matters": "Changes which controls or details are visible without leaving the current page.",
    "notMeaning": "Opening or hiding a panel does not start or stop reception.",
    "category": "Guide"
  },
  "title-Show vessels from all agents on map": {
    "term": "Show vessels from all agents on map",
    "meaning": "Show vessels from all agents on map",
    "matters": "Check this before starting reception or interpreting received data.",
    "notMeaning": "Availability of a source does not guarantee reception.",
    "category": "Guide"
  },
  "title-Signal quality (messages/sec)": {
    "term": "Signal quality (messages/sec)",
    "meaning": "Number of AIS messages arriving per second.",
    "matters": "Helps check whether the selected source is delivering reports.",
    "notMeaning": "Message rate is not a direct measurement of RF signal strength.",
    "category": "Guide"
  },
  "title-Distress alerts": {
    "term": "Distress alerts",
    "meaning": "Counts received DSC distress alerts.",
    "matters": "Draws attention to distress messages heard by the decoder.",
    "notMeaning": "A decoded alert alone is not independent confirmation of an emergency.",
    "category": "Guide"
  },
  "title-Urgency alerts": {
    "term": "Urgency alerts",
    "meaning": "Counts received DSC urgency messages.",
    "matters": "Separates urgent messages from ordinary vessel reports.",
    "notMeaning": "It is not an independently verified incident count.",
    "category": "Guide"
  },
  "title-Show vessel trails": {
    "term": "Show vessel trails",
    "meaning": "Show vessel trails",
    "matters": "Changes which information is drawn or listed in this view.",
    "notMeaning": "A display choice does not change what the receiver can hear.",
    "category": "Guide"
  },
  "title-Name and speed beside each vessel, when zoomed in": {
    "term": "Name and speed beside each vessel, when zoomed in",
    "meaning": "Shows contact labels beside markers when map zoom allows.",
    "matters": "Helps identify contacts without opening each one.",
    "notMeaning": "Hiding labels does not stop receiving reports.",
    "category": "Guide"
  },
  "title-SDR device": {
    "term": "SDR device",
    "meaning": "The software-defined radio assigned to this decoder.",
    "matters": "Different modes may need separate receivers or frequency bands.",
    "notMeaning": "Selecting a device does not start reception by itself.",
    "category": "Guide"
  },
  "title-Gain": {
    "term": "Gain",
    "meaning": "Receiver amplification. Higher values amplify both signals and noise.",
    "matters": "Adjust it to decode weak signals without overloading the receiver.",
    "notMeaning": "Higher gain does not always improve reception.",
    "category": "Guide"
  },
  "title-DSC SDR device (secondary)": {
    "term": "DSC SDR device (secondary)",
    "meaning": "DSC SDR device (secondary)",
    "matters": "Check this before starting reception or interpreting received data.",
    "notMeaning": "Availability of a source does not guarantee reception.",
    "category": "Guide"
  },
  "title-Toggle sidebar": {
    "term": "Toggle sidebar",
    "meaning": "Toggle sidebar.",
    "matters": "Changes which controls or details are visible without leaving the current page.",
    "notMeaning": "Opening or hiding a panel does not start or stop reception.",
    "category": "Guide"
  },
  "title-Connection Type": {
    "term": "Connection Type",
    "meaning": "Connection Type",
    "matters": "Check this before starting reception or interpreting received data.",
    "notMeaning": "Availability of a source does not guarantee reception.",
    "category": "Guide"
  },
  "title-Device": {
    "term": "Device",
    "meaning": "Device",
    "matters": "Check this before starting reception or interpreting received data.",
    "notMeaning": "Availability of a source does not guarantee reception.",
    "category": "Guide"
  },
  "title-Hostname/IP for TCP": {
    "term": "Hostname/IP for TCP",
    "meaning": "Hostname/IP for TCP",
    "matters": "Check this before starting reception or interpreting received data.",
    "notMeaning": "Availability of a source does not guarantee reception.",
    "category": "Guide"
  },
  "title-Fetch messages sent before you connected, from a Store & Forward router on the mesh": {
    "term": "Fetch messages sent before you connected, from a Store & Forward router on the mesh",
    "meaning": "Requests stored messages from a compatible Store & Forward router.",
    "matters": "May retrieve traffic missed while disconnected.",
    "notMeaning": "A suitable router must be reachable; it may not hold every message.",
    "category": "Guide"
  },
  "title-Hide packets that aren't text messages, such as [UNKNOWN] ones from channels you have no key for": {
    "term": "Hide packets that aren't text messages, such as [UNKNOWN] ones from channels you have no key for",
    "meaning": "Hide packets that aren't text messages, such as [UNKNOWN] ones from channels you have no key for",
    "matters": "Adds context to an observation that may need your attention.",
    "notMeaning": "A label or alert alone does not establish identity, intent or danger.",
    "category": "Guide"
  },
  "title-Cancel reply": {
    "term": "Cancel reply",
    "meaning": "Clears the reply target from the message composer.",
    "matters": "Use it to leave a reply thread before composing another message.",
    "notMeaning": "It does not delete an already sent message.",
    "category": "Guide"
  },
  "title-Channel to send on": {
    "term": "Channel to send on",
    "meaning": "Selects the configured mesh channel for the outgoing message.",
    "matters": "Recipients need compatible channel settings and keys.",
    "notMeaning": "Choosing a channel does not guarantee message delivery.",
    "category": "Guide"
  },
  "title-Destination node ID or ^all for broadcast": {
    "term": "Destination node ID or ^all for broadcast",
    "meaning": "Addresses an outgoing mesh message to a node or to all nodes.",
    "matters": "Check the destination before sending.",
    "notMeaning": "A broadcast is not a private message.",
    "category": "Guide"
  },
  "title-Send message": {
    "term": "Send message",
    "meaning": "Composes or sends a mesh message to the selected destination.",
    "matters": "Lets you communicate through the connected radio.",
    "notMeaning": "Delivery still depends on a working route and compatible settings.",
    "category": "Guide"
  },
  "title-direwolf": {
    "term": "direwolf",
    "meaning": "Dire Wolf is a software packet-radio modem used by APRS reception.",
    "matters": "The indicator helps check whether this decoder is available.",
    "notMeaning": "Tool availability does not mean a packet was received.",
    "category": "Guide"
  },
  "title-multimon-ng": {
    "term": "multimon-ng",
    "meaning": "A decoder for several radio data formats.",
    "matters": "Used by reception tools to turn demodulated audio into messages.",
    "notMeaning": "Installed software does not guarantee a supported signal is present.",
    "category": "Guide"
  },
  "title-No active streams": {
    "term": "No active streams",
    "meaning": "No decoder stream is currently reported as active.",
    "matters": "Check the source and start the intended mode if needed.",
    "notMeaning": "It does not mean the radio spectrum is quiet.",
    "category": "Guide"
  },
  "title-Return to Main Dashboard": {
    "term": "Return to Main Dashboard",
    "meaning": "Return to Main Dashboard.",
    "matters": "Opens the named view or changes the named interface preference.",
    "notMeaning": "This control is separate from the radio decoder settings.",
    "category": "Guide"
  },
  "title-Toggle Light/Dark Theme": {
    "term": "Toggle Light/Dark Theme",
    "meaning": "Toggle Light/Dark Theme.",
    "matters": "Changes which controls or details are visible without leaving the current page.",
    "notMeaning": "Opening or hiding a panel does not start or stop reception.",
    "category": "Guide"
  },
  "title-Messages: search everything decoded": {
    "term": "Messages: search everything decoded",
    "meaning": "Messages: search everything decoded.",
    "matters": "Opens the named view or changes the named interface preference.",
    "notMeaning": "This control is separate from the radio decoder settings.",
    "category": "Guide"
  },
  "title-Help & Documentation": {
    "term": "Help & Documentation",
    "meaning": "Help & Documentation.",
    "matters": "Shows reference information for operating the interface.",
    "notMeaning": "Reference information does not check your receiver configuration.",
    "category": "Guide"
  },
  "title-Recent notifications": {
    "term": "Recent notifications",
    "meaning": "Recent notifications.",
    "matters": "Opens the named view or changes the named interface preference.",
    "notMeaning": "This control is separate from the radio decoder settings.",
    "category": "Guide"
  },
  "title-More tools": {
    "term": "More tools",
    "meaning": "More tools.",
    "matters": "Opens the named view or changes the named interface preference.",
    "notMeaning": "This control is separate from the radio decoder settings.",
    "category": "Guide"
  },
  "title-Switch display mode": {
    "term": "Switch display mode",
    "meaning": "Switch display mode",
    "matters": "Changes which information is drawn or listed in this view.",
    "notMeaning": "A display choice does not change what the receiver can hear.",
    "category": "Guide"
  },
  "title-Network Monitor - Multi-Agent View": {
    "term": "Network Monitor - Multi-Agent View",
    "meaning": "Network Monitor - Multi-Agent View",
    "matters": "Check this before starting reception or interpreting received data.",
    "notMeaning": "Availability of a source does not guarantee reception.",
    "category": "Guide"
  },
  "title-Manage Remote Agents": {
    "term": "Manage Remote Agents",
    "meaning": "Manage Remote Agents",
    "matters": "Check this before starting reception or interpreting received data.",
    "notMeaning": "Availability of a source does not guarantee reception.",
    "category": "Guide"
  },
  "title-Toggle voice alerts": {
    "term": "Toggle voice alerts",
    "meaning": "Toggle voice alerts",
    "matters": "Adds context to an observation that may need your attention.",
    "notMeaning": "A label or alert alone does not establish identity, intent or danger.",
    "category": "Guide"
  },
  "title-Mode cheat sheet (Alt+C)": {
    "term": "Mode cheat sheet (Alt+C)",
    "meaning": "Mode cheat sheet (Alt+C).",
    "matters": "Shows reference information for operating the interface.",
    "notMeaning": "Reference information does not check your receiver configuration.",
    "category": "Guide"
  },
  "title-Keyboard shortcuts (Alt+K)": {
    "term": "Keyboard shortcuts (Alt+K)",
    "meaning": "Keyboard shortcuts (Alt+K).",
    "matters": "Shows reference information for operating the interface.",
    "notMeaning": "Reference information does not check your receiver configuration.",
    "category": "Guide"
  },
  "title-Logout": {
    "term": "Logout",
    "meaning": "Logout.",
    "matters": "Opens the named view or changes the named interface preference.",
    "notMeaning": "This control is separate from the radio decoder settings.",
    "category": "Guide"
  },
  "title-Stop all running processes": {
    "term": "Stop all running processes",
    "meaning": "Stops running decoder and scanning processes.",
    "matters": "Use it to release receivers or stop unwanted work.",
    "notMeaning": "This affects all running modes, not just the view on screen.",
    "category": "Guide"
  },
  "title-Toggle theme": {
    "term": "Toggle theme",
    "meaning": "Toggle theme.",
    "matters": "Changes which controls or details are visible without leaving the current page.",
    "notMeaning": "Opening or hiding a panel does not start or stop reception.",
    "category": "Guide"
  },
  "title-Messages": {
    "term": "Messages",
    "meaning": "Decoded messages counted or listed by this view.",
    "matters": "Helps check whether data is arriving.",
    "notMeaning": "A high count does not guarantee complete or error-free reception.",
    "category": "Guide"
  },
  "title-Help": {
    "term": "Help",
    "meaning": "Help.",
    "matters": "Shows reference information for operating the interface.",
    "notMeaning": "Reference information does not check your receiver configuration.",
    "category": "Guide"
  },
  "title-hackrf_transfer": {
    "term": "hackrf_transfer",
    "meaning": "Checks the HackRF capture and transfer tool.",
    "matters": "This tool is needed for the supported HackRF recording operations.",
    "notMeaning": "An installed tool does not mean compatible hardware is connected.",
    "category": "Guide"
  },
  "title-hackrf_sweep": {
    "term": "hackrf_sweep",
    "meaning": "Checks the HackRF spectrum-sweep tool.",
    "matters": "This tool is needed for the supported HackRF sweep operations.",
    "notMeaning": "Tool availability does not mean a sweep is running.",
    "category": "Guide"
  },
  "title-Generic ISM default": {
    "term": "Generic ISM default",
    "meaning": "Generic ISM default",
    "matters": "The setting must suit the signal and hardware you are using.",
    "notMeaning": "A setting alone does not confirm that a signal can be decoded.",
    "category": "Guide"
  },
  "title-PWM common variant": {
    "term": "PWM common variant",
    "meaning": "PWM common variant",
    "matters": "The setting must suit the signal and hardware you are using.",
    "notMeaning": "A setting alone does not confirm that a signal can be decoded.",
    "category": "Guide"
  },
  "title-Generic 2:1 ratio": {
    "term": "Generic 2:1 ratio",
    "meaning": "Generic 2:1 ratio",
    "matters": "The setting must suit the signal and hardware you are using.",
    "notMeaning": "A setting alone does not confirm that a signal can be decoded.",
    "category": "Guide"
  },
  "title-Long-range keyfob": {
    "term": "Long-range keyfob",
    "meaning": "Long-range keyfob",
    "matters": "The setting must suit the signal and hardware you are using.",
    "notMeaning": "A setting alone does not confirm that a signal can be decoded.",
    "category": "Guide"
  },
  "title-Manchester clock period": {
    "term": "Manchester clock period",
    "meaning": "Manchester clock period",
    "matters": "The setting must suit the signal and hardware you are using.",
    "notMeaning": "A setting alone does not confirm that a signal can be decoded.",
    "category": "Guide"
  },
  "title-Copy to clipboard": {
    "term": "Copy to clipboard",
    "meaning": "Copy to clipboard",
    "matters": "Lets you keep or reuse the information currently offered by this view.",
    "notMeaning": "The output is limited to the information captured by the application.",
    "category": "Guide"
  },
  "title-WiFi": {
    "term": "WiFi",
    "meaning": "Indicates WiFi support or WiFi observations for this item.",
    "matters": "Helps identify which radio layer contributes to the view.",
    "notMeaning": "A WiFi observation does not establish ownership or intent.",
    "category": "Guide"
  },
  "title-Bluetooth": {
    "term": "Bluetooth",
    "meaning": "Indicates Bluetooth support or Bluetooth observations for this item.",
    "matters": "Helps identify which radio layer contributes to the view.",
    "notMeaning": "A Bluetooth fingerprint does not authenticate a device.",
    "category": "Guide"
  },
  "title-RF/SDR": {
    "term": "RF/SDR",
    "meaning": "RF/SDR",
    "matters": "Check this before starting reception or interpreting received data.",
    "notMeaning": "Availability of a source does not guarantee reception.",
    "category": "Guide"
  },
  "title-Opens the client report to print or save as PDF": {
    "term": "Opens the client report to print or save as PDF",
    "meaning": "Opens the client report to print or save as PDF",
    "matters": "Lets you keep or reuse the information currently offered by this view.",
    "notMeaning": "The output is limited to the information captured by the application.",
    "category": "Guide"
  },
  "title-Temperature by altitude": {
    "term": "Temperature by altitude",
    "meaning": "A profile of temperature readings against reported balloon altitude.",
    "matters": "Helps follow changes through the balloon’s ascent.",
    "notMeaning": "It describes received telemetry, not every location at that height.",
    "category": "Guide"
  },
  "title-Refresh port list": {
    "term": "Refresh port list",
    "meaning": "Refresh port list",
    "matters": "Check this before starting reception or interpreting received data.",
    "notMeaning": "Availability of a source does not guarantee reception.",
    "category": "Guide"
  },
  "title-Deauth clients so they reconnect and produce a handshake (authorized testing only)": {
    "term": "Deauth clients so they reconnect and produce a handshake (authorized testing only)",
    "meaning": "Deauth clients so they reconnect and produce a handshake (authorized testing only)",
    "matters": "Adds context to an observation that may need your attention.",
    "notMeaning": "A label or alert alone does not establish identity, intent or danger.",
    "category": "Guide"
  },
  "title-Detect IRKs from paired devices": {
    "term": "Detect IRKs from paired devices",
    "meaning": "Detect IRKs from paired devices",
    "matters": "Check this before starting reception or interpreting received data.",
    "notMeaning": "Availability of a source does not guarantee reception.",
    "category": "Guide"
  },
  "title-Has position": {
    "term": "Has position",
    "meaning": "This record has position information available to the map.",
    "matters": "Lets you connect a message or device with its displayed location.",
    "notMeaning": "The position may be old or self-reported.",
    "category": "Guide"
  },
  "title-Refresh agent state": {
    "term": "Refresh agent state",
    "meaning": "Refresh agent state",
    "matters": "Check this before starting reception or interpreting received data.",
    "notMeaning": "Availability of a source does not guarantee reception.",
    "category": "Guide"
  },
  "title-Click to select": {
    "term": "Click to select",
    "meaning": "Click to select",
    "matters": "Open this item to inspect its recorded details.",
    "notMeaning": "Recorded details may be incomplete or out of date.",
    "category": "Guide"
  },
  "title-Download": {
    "term": "Download",
    "meaning": "Download",
    "matters": "Lets you keep or reuse the information currently offered by this view.",
    "notMeaning": "The output is limited to the information captured by the application.",
    "category": "Guide"
  },
  "title-Delete": {
    "term": "Delete",
    "meaning": "Delete",
    "matters": "Use this when the selected record or view is no longer needed.",
    "notMeaning": "Check the selected item before using a removal control.",
    "category": "Guide"
  },
  "title-Generate QR Code": {
    "term": "Generate QR Code",
    "meaning": "Builds a QR code for the selected mesh channel configuration.",
    "matters": "Helps transfer channel settings to another device.",
    "notMeaning": "Sharing channel details may also share access to that channel.",
    "category": "Guide"
  },
  "title-On map": {
    "term": "On map",
    "meaning": "This record has position information available to the map.",
    "matters": "Lets you connect a message or device with its displayed location.",
    "notMeaning": "The position may be old or self-reported.",
    "category": "Guide"
  },
  "title-No position reported": {
    "term": "No position reported",
    "meaning": "No position reported",
    "matters": "Lets you keep or reuse the information currently offered by this view.",
    "notMeaning": "The output is limited to the information captured by the application.",
    "category": "Guide"
  },
  "title-Remove from the device's node list": {
    "term": "Remove from the device's node list",
    "meaning": "Remove from the device's node list",
    "matters": "Use this when the selected record or view is no longer needed.",
    "notMeaning": "Check the selected item before using a removal control.",
    "category": "Guide"
  },
  "title-Message this node": {
    "term": "Message this node",
    "meaning": "Composes or sends a mesh message to the selected destination.",
    "matters": "Lets you communicate through the connected radio.",
    "notMeaning": "Delivery still depends on a working route and compatible settings.",
    "category": "Guide"
  },
  "title-Reply": {
    "term": "Reply",
    "meaning": "Composes or sends a mesh message to the selected destination.",
    "matters": "Lets you communicate through the connected radio.",
    "notMeaning": "Delivery still depends on a working route and compatible settings.",
    "category": "Guide"
  },
  "title-Right-click to remove": {
    "term": "Right-click to remove",
    "meaning": "Right-click to remove",
    "matters": "Use this when the selected record or view is no longer needed.",
    "notMeaning": "Check the selected item before using a removal control.",
    "category": "Guide"
  },
  "title-Frequencies": {
    "term": "Frequencies",
    "meaning": "Frequencies",
    "matters": "Open this item to inspect its recorded details.",
    "notMeaning": "Recorded details may be incomplete or out of date.",
    "category": "Guide"
  },
  "title-Click for details": {
    "term": "Click for details",
    "meaning": "Click for details",
    "matters": "Open this item to inspect its recorded details.",
    "notMeaning": "Recorded details may be incomplete or out of date.",
    "category": "Guide"
  },
  "title-Download hashcat .hc22000 for offline cracking": {
    "term": "Download hashcat .hc22000 for offline cracking",
    "meaning": "Download hashcat .hc22000 for offline cracking",
    "matters": "Lets you keep or reuse the information currently offered by this view.",
    "notMeaning": "The output is limited to the information captured by the application.",
    "category": "Guide"
  },
  "title-Download the raw .cap capture": {
    "term": "Download the raw .cap capture",
    "meaning": "Download the raw .cap capture",
    "matters": "Lets you keep or reuse the information currently offered by this view.",
    "notMeaning": "The output is limited to the information captured by the application.",
    "category": "Guide"
  },
  "title-Tracker": {
    "term": "Tracker",
    "meaning": "Tracker",
    "matters": "Adds context to an observation that may need your attention.",
    "notMeaning": "A label or alert alone does not establish identity, intent or danger.",
    "category": "Guide"
  },
  "title-Open OOK decoder tuned to this frequency": {
    "term": "Open OOK decoder tuned to this frequency",
    "meaning": "Open OOK decoder tuned to this frequency",
    "matters": "The setting must suit the signal and hardware you are using.",
    "notMeaning": "A setting alone does not confirm that a signal can be decoded.",
    "category": "Guide"
  },
  "title-Link the current sweep to a case": {
    "term": "Link the current sweep to a case",
    "meaning": "Associates the current survey sweep with a case record.",
    "matters": "Keeps related inspection evidence together.",
    "notMeaning": "Linking a sweep does not validate its findings.",
    "category": "Guide"
  },
  "title-Known device": {
    "term": "Known device",
    "meaning": "Known device",
    "matters": "Check this before starting reception or interpreting received data.",
    "notMeaning": "Availability of a source does not guarantee reception.",
    "category": "Guide"
  },
  "title-Add to ignore list (my device)": {
    "term": "Add to ignore list (my device)",
    "meaning": "Add to ignore list (my device)",
    "matters": "Check this before starting reception or interpreting received data.",
    "notMeaning": "Availability of a source does not guarantee reception.",
    "category": "Guide"
  },
  "title-WiFi client": {
    "term": "WiFi client",
    "meaning": "WiFi client",
    "matters": "Adds context to an observation that may need your attention.",
    "notMeaning": "A label or alert alone does not establish identity, intent or danger.",
    "category": "Guide"
  },
  "title-Audio-capable device": {
    "term": "Audio-capable device",
    "meaning": "Audio-capable device",
    "matters": "Check this before starting reception or interpreting received data.",
    "notMeaning": "Availability of a source does not guarantee reception.",
    "category": "Guide"
  },
  "title-Remove bookmark": {
    "term": "Remove bookmark",
    "meaning": "Remove bookmark",
    "matters": "Use this when the selected record or view is no longer needed.",
    "notMeaning": "Check the selected item before using a removal control.",
    "category": "Guide"
  },
  "title-Delete image": {
    "term": "Delete image",
    "meaning": "Delete image",
    "matters": "Use this when the selected record or view is no longer needed.",
    "notMeaning": "Check the selected item before using a removal control.",
    "category": "Guide"
  },
  "title-Recent trend": {
    "term": "Recent trend",
    "meaning": "Change across recent readings shown by this view.",
    "matters": "Helps spot a rising or falling measurement.",
    "notMeaning": "A trend does not explain its cause.",
    "category": "Guide"
  },
  "title-Hide baseline signals": {
    "term": "Hide baseline signals",
    "meaning": "Hides observations already represented in the baseline.",
    "matters": "Makes deviations easier to inspect.",
    "notMeaning": "Baseline signals can still be present and received.",
    "category": "Guide"
  },
  "title-Show only new signals": {
    "term": "Show only new signals",
    "meaning": "Filters the display to signals marked as new.",
    "matters": "Helps focus on changes from earlier observations.",
    "notMeaning": "New does not mean malicious.",
    "category": "Guide"
  },
  "title-Show only burst activity": {
    "term": "Show only burst activity",
    "meaning": "Filters the display to activity classified as bursts.",
    "matters": "Helps inspect intermittent transmissions.",
    "notMeaning": "Continuous signals can still be present.",
    "category": "Guide"
  },
  "title-Confidence": {
    "term": "Confidence",
    "meaning": "The tool’s confidence score for a detected pattern.",
    "matters": "Helps prioritise observations for inspection.",
    "notMeaning": "It is a heuristic score, not a measured probability of wrongdoing.",
    "category": "Guide"
  },
  "title-Current RSSI": {
    "term": "Current RSSI",
    "meaning": "Latest received signal-strength indication.",
    "matters": "Compare successive readings from the same receiver.",
    "notMeaning": "It is not an exact distance or a comparison calibrated across devices.",
    "category": "Guide"
  },
  "title-Observation count": {
    "term": "Observation count",
    "meaning": "How many observations have been recorded for this item.",
    "matters": "Repeated sightings provide more context than a single observation.",
    "notMeaning": "A large count does not by itself make an observation suspicious.",
    "category": "Guide"
  },
  "title-Dismiss": {
    "term": "Dismiss",
    "meaning": "Dismiss",
    "matters": "The setting must suit the signal and hardware you are using.",
    "notMeaning": "A setting alone does not confirm that a signal can be decoded.",
    "category": "Guide"
  },
  "title-Messages from this address": {
    "term": "Messages from this address",
    "meaning": "Messages from this address",
    "matters": "Open this item to inspect its recorded details.",
    "notMeaning": "Recorded details may be incomplete or out of date.",
    "category": "Guide"
  },
  "title-Click to view raw data": {
    "term": "Click to view raw data",
    "meaning": "Click to view raw data",
    "matters": "Open this item to inspect its recorded details.",
    "notMeaning": "Recorded details may be incomplete or out of date.",
    "category": "Guide"
  },
  "title-APRS Symbol": {
    "term": "APRS Symbol",
    "meaning": "The symbol included in an APRS station report.",
    "matters": "Helps recognise how a station describes itself.",
    "notMeaning": "A self-reported symbol does not verify the station’s identity.",
    "category": "Guide"
  },
  "title-No signal data available": {
    "term": "No signal data available",
    "meaning": "This item has no signal-strength data to display.",
    "matters": "Avoid treating an empty plot as a measured zero.",
    "notMeaning": "Missing data does not mean the transmitter is absent.",
    "category": "Guide"
  },
  "title-Change from previous reading": {
    "term": "Change from previous reading",
    "meaning": "Change across recent readings shown by this view.",
    "matters": "Helps spot a rising or falling measurement.",
    "notMeaning": "A trend does not explain its cause.",
    "category": "Guide"
  },
  "reading-NOW": {
    "term": "Current aircraft",
    "meaning": "Aircraft currently retained in the live view.",
    "matters": "Shows how many contacts are being displayed.",
    "notMeaning": "It is not a count of every aircraft in the area.",
    "category": "Reading"
  },
  "reading-VESSELS": {
    "term": "Current vessels",
    "meaning": "Vessels currently retained in the live AIS view.",
    "matters": "Shows how many contacts are being displayed.",
    "notMeaning": "Vessels without received AIS reports are absent.",
    "category": "Reading"
  },
  "reading-SEEN": {
    "term": "Contacts seen",
    "meaning": "Distinct contacts counted during this session.",
    "matters": "Helps distinguish total activity from contacts still on screen.",
    "notMeaning": "It is limited to reports received during this session.",
    "category": "Reading"
  },
  "reading-MAX NM": {
    "term": "Furthest contact",
    "meaning": "Greatest received contact distance, in nautical miles.",
    "matters": "Helps compare the reception achieved from this observer position.",
    "notMeaning": "It is not a guaranteed reception range.",
    "category": "Reading"
  },
  "reading-NEAR NM": {
    "term": "Nearest contact",
    "meaning": "Distance to the nearest displayed contact, in nautical miles.",
    "matters": "Helps find nearby activity relative to the observer.",
    "notMeaning": "An incorrect observer location makes this distance misleading.",
    "category": "Reading"
  },
  "reading-HIGH FL": {
    "term": "Highest flight level",
    "meaning": "Highest reported flight level, in hundreds of feet.",
    "matters": "Summarises altitude among received aircraft reports.",
    "notMeaning": "Flight level uses pressure altitude, not height above terrain.",
    "category": "Reading"
  },
  "reading-FAST KT": {
    "term": "Fastest aircraft",
    "meaning": "Highest reported aircraft speed in knots.",
    "matters": "Summarises movement in received reports.",
    "notMeaning": "A speed report may be stale or erroneous.",
    "category": "Reading"
  },
  "reading-MAX KT": {
    "term": "Fastest vessel",
    "meaning": "Highest reported vessel speed in knots.",
    "matters": "Summarises movement in received AIS reports.",
    "notMeaning": "The value is not an independently verified measurement.",
    "category": "Reading"
  },
  "reading-COUNTRIES": {
    "term": "Countries",
    "meaning": "Countries inferred from received aircraft identities.",
    "matters": "Helps summarise the registered origins of contacts.",
    "notMeaning": "Registration does not show the flight’s origin or destination.",
    "category": "Reading"
  },
  "reading-ACARS": {
    "term": "ACARS messages",
    "meaning": "Aircraft datalink messages received by the ACARS decoder.",
    "matters": "May add operational context to tracked flights.",
    "notMeaning": "Not all messages can be linked to an aircraft on the map.",
    "category": "Reading"
  },
  "reading-VDL2": {
    "term": "VDL Mode 2",
    "meaning": "Digital VHF aircraft datalink traffic decoded by the VDL2 tool.",
    "matters": "Offers another source of aircraft messages.",
    "notMeaning": "Not every packet contains readable text or a position.",
    "category": "Reading"
  },
  "reading-SESSION": {
    "term": "Session time",
    "meaning": "Elapsed time for the current dashboard session.",
    "matters": "Helps put accumulated counts in context.",
    "notMeaning": "It is not the age of each displayed report.",
    "category": "Reading"
  },
  "reading-STATIONS": {
    "term": "APRS stations",
    "meaning": "Stations observed in decoded APRS packets.",
    "matters": "Shows identities contributing reports to this view.",
    "notMeaning": "A station may have stopped transmitting since its last report.",
    "category": "Reading"
  },
  "reading-MHz": {
    "term": "Frequency",
    "meaning": "Receiver frequency in megahertz.",
    "matters": "Must match the transmission you intend to decode.",
    "notMeaning": "The same frequency can carry several incompatible signal types.",
    "category": "Reading"
  },
  "reading-NODE": {
    "term": "Connected node",
    "meaning": "Name reported by the connected mesh radio.",
    "matters": "Confirms which local device you are using.",
    "notMeaning": "A name is not an authenticated identity.",
    "category": "Reading"
  },
  "reading-ID": {
    "term": "Node ID",
    "meaning": "Identifier reported by the connected mesh radio.",
    "matters": "Helps distinguish it from other nodes.",
    "notMeaning": "An identifier alone does not prove ownership.",
    "category": "Reading"
  },
  "reading-MODEL": {
    "term": "Radio model",
    "meaning": "Hardware model reported by the connected radio.",
    "matters": "Helps check which device is connected.",
    "notMeaning": "The model alone does not establish reception quality.",
    "category": "Reading"
  },
  "reading-SATS": {
    "term": "GPS satellites",
    "meaning": "Satellite count reported by the mesh device’s GPS.",
    "matters": "Helps assess whether its positioning receiver sees satellites.",
    "notMeaning": "A count alone does not establish position accuracy.",
    "category": "Reading"
  },
  "reading-LAT": {
    "term": "ISS latitude",
    "meaning": "Predicted latitude of the space station.",
    "matters": "Locates its ground track north or south of the equator.",
    "notMeaning": "This is an orbital prediction, not a position received by your antenna.",
    "category": "Reading"
  },
  "reading-LON": {
    "term": "ISS longitude",
    "meaning": "Predicted longitude of the space station.",
    "matters": "Locates its ground track east or west of Greenwich.",
    "notMeaning": "This is an orbital prediction, not a measured radio position.",
    "category": "Reading"
  },
  "reading-ALT km": {
    "term": "ISS altitude",
    "meaning": "Predicted station height in kilometres.",
    "matters": "Helps describe the current orbit.",
    "notMeaning": "It is not distance from your receiver.",
    "category": "Reading"
  },
  "reading-km/h": {
    "term": "ISS speed",
    "meaning": "Predicted orbital speed in kilometres per hour.",
    "matters": "Shows how quickly the station moves in orbit.",
    "notMeaning": "It is not its speed toward your observer location.",
    "category": "Reading"
  },
  "reading-SUNLIGHT": {
    "term": "ISS sunlight",
    "meaning": "Whether the predicted station position is illuminated by the Sun.",
    "matters": "Useful context when planning visual observation.",
    "notMeaning": "Illumination does not guarantee visibility through clouds or daylight.",
    "category": "Reading"
  },
  "reading-satellites": {
    "term": "Tracked satellites",
    "meaning": "Satellites selected for this dashboard.",
    "matters": "Defines which objects contribute predictions.",
    "notMeaning": "Tracking here does not mean a radio has received them.",
    "category": "Reading"
  },
  "reading-visible": {
    "term": "Visible satellites",
    "meaning": "Tracked satellites predicted above the observer’s horizon.",
    "matters": "Helps find potential passes now.",
    "notMeaning": "Above the horizon does not guarantee naked-eye visibility or reception.",
    "category": "Reading"
  },
  "reading-passes": {
    "term": "Predicted passes",
    "meaning": "Passes calculated for the selected satellites and observer.",
    "matters": "Helps plan reception sessions.",
    "notMeaning": "A pass prediction does not confirm a transmission.",
    "category": "Reading"
  },
  "reading-best el": {
    "term": "Best elevation",
    "meaning": "Highest predicted pass elevation in the dashboard’s pass window.",
    "matters": "Higher passes can offer a clearer line of sight.",
    "notMeaning": "It does not account for every local obstruction.",
    "category": "Reading"
  },
  "reading-MSGS": {
    "term": "Messages",
    "meaning": "Decoded messages counted or listed by this view.",
    "matters": "Helps check whether data is arriving.",
    "notMeaning": "A high count does not guarantee complete or error-free reception.",
    "category": "Guide"
  },
  "reading-NODES": {
    "term": "Nodes",
    "meaning": "Devices known to the connected mesh radio.",
    "matters": "Shows available identities and their last reported details.",
    "notMeaning": "A known node is not necessarily online or reachable now.",
    "category": "Guide"
  },
  "reading-PACKETS": {
    "term": "Packets",
    "meaning": "Packets received or decoded by the active tool.",
    "matters": "Shows activity reaching the receiver.",
    "notMeaning": "Not every packet contains a position or readable text.",
    "category": "Guide"
  },
  "reading-SIGNAL": {
    "term": "Signal",
    "meaning": "Reception activity reported by the selected source.",
    "matters": "Helps tell whether reports are reaching the dashboard.",
    "notMeaning": "It is not a calibrated measurement of antenna performance.",
    "category": "Guide"
  },
  "reading-SOURCE": {
    "term": "Source",
    "meaning": "The local receiver or remote agent supplying this view.",
    "matters": "Check it before interpreting data or starting a decoder.",
    "notMeaning": "An agent’s reception conditions may differ from your local antenna.",
    "category": "Guide"
  },
  "connect": {
    "term": "Connect radio",
    "meaning": "Opens a connection to the selected mesh radio using the configured transport.",
    "matters": "Required before exchanging messages through that device.",
    "notMeaning": "A connection does not guarantee that another mesh node is reachable.",
    "category": "Guide"
  },
  "disconnect": {
    "term": "Disconnect radio",
    "meaning": "Closes this application’s connection to the mesh radio.",
    "matters": "Releases the connection when you have finished.",
    "notMeaning": "It does not necessarily power off the radio or stop its own transmissions.",
    "category": "Guide"
  },
  "transport": {
    "term": "Connection transport",
    "meaning": "Chooses serial, TCP or Bluetooth where supported by this mode.",
    "matters": "The address and connection settings must match the radio.",
    "notMeaning": "Selecting a transport does not connect automatically.",
    "category": "Guide"
  },
  "baud": {
    "term": "Serial baud rate",
    "meaning": "Serial communication speed used to talk to the radio.",
    "matters": "It must match the device’s serial configuration.",
    "notMeaning": "It does not set the over-the-air radio data rate.",
    "category": "Guide"
  },
  "start": {
    "term": "Start decoder",
    "meaning": "Starts the selected decoder using this view’s receiver and settings.",
    "matters": "Check the source, frequency and device before starting.",
    "notMeaning": "Starting a decoder does not guarantee that messages will be received.",
    "category": "Guide"
  },
  "stop": {
    "term": "Stop decoder",
    "meaning": "Stops the decoder controlled by this view.",
    "matters": "Releases its receiver and ends live decoding.",
    "notMeaning": "It does not stop transmitters or other independent modes.",
    "category": "Guide"
  },
  "aprs-region": {
    "term": "APRS region",
    "meaning": "Selects the regional APRS frequency preset or a custom frequency.",
    "matters": "Different regions use different APRS channels.",
    "notMeaning": "A preset does not guarantee an active local station.",
    "category": "Guide"
  },
  "tle-add": {
    "term": "Add orbital elements",
    "meaning": "Adds a satellite using supplied two-line orbital elements.",
    "matters": "Lets the dashboard predict passes for that object.",
    "notMeaning": "Orbital elements age and do not describe current radio activity.",
    "category": "Guide"
  },
  "tle-refresh": {
    "term": "Refresh orbital elements",
    "meaning": "Updates the orbital elements used by tracked satellites.",
    "matters": "Fresh elements improve the usefulness of pass predictions.",
    "notMeaning": "An update may need an available data provider.",
    "category": "Guide"
  },
  "scheduler-enable": {
    "term": "Enable capture scheduler",
    "meaning": "Enables ground-station capture scheduling for configured satellite profiles.",
    "matters": "Use after checking receivers, frequencies and decoder tasks.",
    "notMeaning": "A scheduled capture can still fail due to reception or unavailable hardware.",
    "category": "Guide"
  },
  "scheduler-disable": {
    "term": "Disable capture scheduler",
    "meaning": "Disables future automatic ground-station scheduling.",
    "matters": "Use when automatic reception is no longer wanted.",
    "notMeaning": "Use the active-capture Stop control to end a running capture.",
    "category": "Guide"
  },
  "capture-stop": {
    "term": "Stop active capture",
    "meaning": "Stops the currently active ground-station capture.",
    "matters": "Use to release its receiver or end a failed capture.",
    "notMeaning": "Stopping now does not improve data already captured.",
    "category": "Guide"
  },
  "map-follow": {
    "term": "Follow satellite",
    "meaning": "Keeps the map centred on the active satellite.",
    "matters": "Makes it easier to follow its predicted movement.",
    "notMeaning": "This changes the map view, not antenna pointing or receiver tuning.",
    "category": "Guide"
  },
  "iss-range": {
    "term": "ISS slant range",
    "meaning": "Predicted straight-line distance from your observer location to the station.",
    "matters": "Helps interpret the geometry of the current pass.",
    "notMeaning": "It is not distance along the Earth’s surface or a measured radio range.",
    "category": "Guide"
  },
  "cabin": {
    "term": "Cabin pressure",
    "meaning": "Station cabin pressure from the telemetry feed, in pounds per square inch.",
    "matters": "Shows one environmental measurement when the feed is available.",
    "notMeaning": "It is not measured by your local radio or a local air-pressure sensor.",
    "category": "Guide"
  },
  "oxygen": {
    "term": "Oxygen partial pressure",
    "meaning": "Oxygen’s share of the cabin pressure from the telemetry feed, in psia.",
    "matters": "Describes oxygen pressure rather than just its percentage.",
    "notMeaning": "A missing value is not a report of zero oxygen.",
    "category": "Guide"
  },
  "co2": {
    "term": "Carbon dioxide partial pressure",
    "meaning": "Carbon dioxide’s share of cabin pressure from the telemetry feed, in psia.",
    "matters": "Provides context on the reported cabin environment.",
    "notMeaning": "A missing or stale reading does not establish current cabin conditions.",
    "category": "Guide"
  },
  "sarj": {
    "term": "Solar array rotary joint",
    "meaning": "Reported angle of the port or starboard solar alpha rotary joint, in degrees.",
    "matters": "Shows the orientation used to rotate the station’s solar arrays.",
    "notMeaning": "This is feed data, not an angle measured by your antenna.",
    "category": "Guide"
  },
  "attitude-rate": {
    "term": "Attitude rate",
    "meaning": "Magnitude of the station’s reported rotation rates, in degrees per second.",
    "matters": "Summarises how quickly its orientation is changing.",
    "notMeaning": "It is not the station’s orbital speed.",
    "category": "Guide"
  },
  "serial-port": {
    "term": "Serial port",
    "meaning": "The operating-system serial port used to connect to the mesh radio.",
    "matters": "Choose the port belonging to your intended device.",
    "notMeaning": "It is not the radio’s over-the-air frequency.",
    "category": "Guide"
  },
  "receiver": {
    "term": "Receiver",
    "meaning": "The receiver assigned to this reception task.",
    "matters": "Check that the correct hardware or remote receiver is selected.",
    "notMeaning": "Selecting a receiver does not guarantee that it is available or tuned.",
    "category": "Guide"
  },
  "decoder-task": {
    "term": "Decoder task",
    "meaning": "The decoder used for this ground-station profile.",
    "matters": "Its format must match the satellite transmission.",
    "notMeaning": "The choice does not identify an unknown signal automatically.",
    "category": "Guide"
  },
  "tracking-toggle": {
    "term": "Start or stop tracking",
    "category": "Control",
    "meaning": "Starts reception with the selected source and settings, or stops it when already running.",
    "matters": "Check the selected receiver before using this control.",
    "notMeaning": "Starting reception does not guarantee that contacts will be heard."
  }
}; /* end catalogue */

  // Preferences live inside the existing account-synced intercept_settings object.
  function prefs() {
    try { return JSON.parse(localStorage.getItem('intercept_settings') || '{}'); }
    catch { return {}; }
  }
  const enabled = () => prefs()['explain.enabled'] !== false;
  const delay = () => {
    const value = Number(prefs()['explain.delay']);
    return [300, 1000, 2000].includes(value) ? value : 1000;
  };
  const fallback = text => ({ term: text, meaning: text, category: 'Details' });
  function itemFor(anchor) {
    if (anchor.dataset.explain) return guide[anchor.dataset.explain];
    const text = anchor.dataset.explainText;
    return guide['title-' + text] || guide['term-' + text] || fallback(text);
  }
  function speak(text) {
    if (window.InterceptAMI) { window.InterceptAMI.speak(text); return; }
    // A frame must never fall back to a second, local voice.
    if (window.parent !== window || !window.speechSynthesis) return;
    window.speechSynthesis.cancel();
    window.speechSynthesis.speak(new SpeechSynthesisUtterance(text));
  }
  const engine = Explain.mount({
    selector: '[data-explain],[data-explain-text]', getItem: itemFor,
    enabled, delay, speak,
    isActionable: anchor => !!anchor.closest('button,a,input,select,label,[role="button"],[onclick]'),
    labels: { notMeaning: "What it doesn't mean", foot: 'Touch: tap once to explain, again to use the control. Escape closes this guide. F1 focuses Read aloud.' }
  });
  const autoLabels = new WeakMap();
  const targetSelector = '[title],[data-tooltip],[data-explain-text],.mode-nav-btn[data-mode],.mobile-nav-btn[data-mode],.strip-stat,.mesh-strip-stat,.meshcore-strip-stat,.stat-badge,.stat-item,.telemetry-item,.stat-card,label';
  function prepare(el) {
    // Never the page itself (<body> carries data-mode, and contains every reading): it would explain everywhere
    if (!(el instanceof HTMLElement) || el === document.body || el === document.documentElement || el.closest('#explainTip')) return;
    // Native/library titles become the same plain-text explanation, with no HTML.
    const native = el.getAttribute('title') || el.getAttribute('data-tooltip');
    if (native) {
      el.dataset.explainText = native;
      el.removeAttribute('title'); el.removeAttribute('data-tooltip');
    }
    if (el.matches('.mode-nav-btn[data-mode],.mobile-nav-btn[data-mode]') && guide['mode-' + el.dataset.mode]) {
      el.dataset.explain = 'mode-' + el.dataset.mode;
    }
    if (!el.dataset.explain && !el.dataset.explainText) {
      const label = el.querySelector('.strip-label,.mesh-strip-label,.meshcore-strip-label,.label,.stat-label,.telemetry-label,.stat-title');
      const text = (label?.textContent || (el.matches('label') ? el.childNodes[0]?.textContent : '') || '').trim().replace(/\s*[:(].*$/, '');
      const term = Object.keys(guide).find(key => key.startsWith('term-') && key.slice(5).toLowerCase() === text?.toLowerCase());
      if (el.querySelector('#issFeedState')) el.dataset.explain = 'mode-iss';
      else if (guide['reading-' + text]) el.dataset.explain = 'reading-' + text;
      else if (term) el.dataset.explain = term;
    }
    if (!el.dataset.explain && !el.dataset.explainText) return;
    const item = itemFor(el);
    if (!item) return;
    const input = el.matches('label') ? el.querySelector('input,select,textarea') : null;
    // Preserve supplied accessible names; icon-only controls get the old title.
    const named = input || el;
    if ((autoLabels.has(named) && named.getAttribute('aria-label') === autoLabels.get(named)) ||
        (!named.hasAttribute('aria-label') && !named.hasAttribute('aria-labelledby') && !named.labels?.length)) {
      named.setAttribute('aria-label', item.term);
      autoLabels.set(named, item.term);
    }
    // Whole reading rows are keyboard targets; labels use their native input.
    if (!input && !el.matches('button,a[href],input,select,textarea,[tabindex]')) el.tabIndex = 0;
  }
  function scan(root) {
    if (root instanceof Element && root.matches(targetSelector)) prepare(root);
    root.querySelectorAll?.(targetSelector).forEach(prepare);
  }
  // Bind measurements to their whole row, and controls to their own app-owned guide.
  const bindings = {
  "startBtn": "tracking-toggle",
  "dscStartBtn": "tracking-toggle",
  "meshStripConnectBtn": "connect",
  "meshStripDisconnectBtn": "disconnect",
  "meshcoreConnectBtn": "connect",
  "meshcoreDisconnectBtn": "disconnect",
  "meshStripConnType": "transport",
  "meshcoreTransportTabs": "transport",
  "meshcoreBaudSelect": "baud",
  "meshcorePortSelect": "serial-port",
  "meshcoreTcpHost": "transport",
  "meshcoreTcpPort": "transport",
  "meshcoreBleSelect": "transport",
  "aprsStripStartBtn": "start",
  "aprsStripStopBtn": "stop",
  "aprsStripRegion": "aprs-region",
  "aprsStripGain": "term-Gain",
  "aprsStripCustomFreq": "term-Frequency",
  "gsEnableBtn": "scheduler-enable",
  "gsDisableBtn": "scheduler-disable",
  "gsStopBtn": "capture-stop",
  "mapFollowBtn": "map-follow",
  "gsReceiverSelect": "receiver",
  "satSelect": "mode-satellite",
  "gsProfFreq": "term-Frequency",
  "gsProfDecoder": "decoder-task",
  "issElev": "term-Elevation",
  "issAz": "term-Azimuth",
  "issRange": "iss-range",
  "telCabin": "cabin",
  "telPpo2": "oxygen",
  "telPpco2": "co2",
  "telSarjP": "sarj",
  "telSarjS": "sarj",
  "telRate": "attitude-rate"
};
  for (const [id, key] of Object.entries(bindings)) {
    const value = document.getElementById(id);
    const target = value?.closest('.iss-kv,.iss-tel-cell') || value;
    if (target) { target.dataset.explain = key; prepare(target); }
  }
  scan(document);
  new MutationObserver(records => {
    for (const record of records) {
      if (record.type === 'attributes') prepare(record.target);
      else for (const node of record.addedNodes) {
        if (node instanceof Element) scan(node);
        // A value update may insert the label after its reading row.
        const row = node.parentElement?.closest('.strip-stat,.mesh-strip-stat,.meshcore-strip-stat,.stat-badge,.stat-item,.telemetry-item,.stat-card');
        if (row) prepare(row);
      }
    }
  }).observe(document.body, { subtree: true, childList: true, attributes: true,
    attributeFilter: ['title', 'data-tooltip', 'data-explain-text'] });

  // The display pane is optional on dedicated dashboards. Use the same settings
  // object everywhere; no additional localStorage key or server setting is needed.
  const pane = document.getElementById('settings-display');
  if (pane) {
    // Settings → Display → Explanations, as in VIGIL: Tooltips ON/OFF and Tooltip delay
    const group = document.createElement('div'); group.className = 'settings-group';
    const title = document.createElement('div'); title.className = 'settings-group-title'; title.textContent = 'Explanations';
    function row(label, desc, choices, current, choose) {
      const r = document.createElement('div'); r.className = 'settings-row';
      const l = document.createElement('div'); l.className = 'settings-label';
      const t = document.createElement('span'); t.className = 'settings-label-text'; t.textContent = label;
      const d = document.createElement('span'); d.className = 'settings-label-desc'; d.textContent = desc;
      l.append(t, d);
      const seg = document.createElement('div'); seg.className = 'settings-seg'; seg.setAttribute('role', 'group'); seg.setAttribute('aria-label', label);
      const buttons = choices.map(([value, text]) => {
        const b = document.createElement('button'); b.type = 'button'; b.textContent = text; b.dataset.value = String(value);
        b.addEventListener('click', () => { choose(value); mark(value); });
        return b;
      });
      function mark(value) { for (const b of buttons) b.setAttribute('aria-pressed', String(b.dataset.value === String(value))); }
      mark(current); seg.append(...buttons); r.append(l, seg);
      return r;
    }
    function save(key, value) {
      const all = prefs(); all[key] = value;
      if (typeof Settings !== 'undefined') Settings._cache[key] = value;
      try { localStorage.setItem('intercept_settings', JSON.stringify(all)); } catch { /* Storage unavailable. */ }
      engine.hide();
    }
    group.append(title,
      row('Tooltips', 'Explain readings and controls on hover or tap', [[true, 'On'], [false, 'Off']], enabled(), v => save('explain.enabled', v)),
      row('Tooltip delay', 'How long to hover before an explanation appears', [[300, 'Short'], [1000, '1s'], [2000, '2s']], delay(), v => save('explain.delay', v)));
    pane.prepend(group);
  }
})();
