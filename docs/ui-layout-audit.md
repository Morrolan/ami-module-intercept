# Intercept information layout audit

Owner rule (2026-11-02): expanding details must reveal all information and push following content down. Work is isolated from Claude in `feat/content-first-layout`.

## Method and evidence

Baseline Chromium inventory rendered every registered mode and all 12 existing dashboard/page smoke targets at 1440×900, dark. It found viewport-constrained main shells, capped selected details, and independently scrolling information cards. A real ADS-B browser regression failed because adding details did not move TRACKED AIRCRAFT and the selected panel clipped content. The repaired ADS-B regression passed 16 combinations: 1440×900, 1366×768, 390×844, and 720×450 (a 200%-zoom-equivalent CSS viewport), both themes and standalone/AMI embed.

Initial selector findings below are candidates until populated geometry tests prove them. Empty panels alone cannot prove content is accessible. Browser tests add synthetic rows and a final action, then check every ancestor for clipping and ensure the action can be brought into view without an inner information scrollbar. No receiver is started.

## Registered modes

The cross-mode browser matrix exercises the common output shell in each mode, including switching modes sequentially (lazy CSS must not reintroduce caps). Rich nested content gets separate fixtures listed below; this is not a claim to have exercised every protocol-specific field or hardware state.

`pager`, `sensor`, `rtlamr`, `subghz`, `gps`, `radiosonde`, `satellite`, `sstv`, `weathersat`, `sstv_general`, `wefax`, `spaceweather`, `meteor`, `wifi`, `bluetooth`, `bt_locate`, `wifi_locate`, `tscm`, `tscmsurvey`, `activity`, `drone`, `spystations`, `websdr`, `waterfall`, `morse`, `system`, `identity_management`, `ook`.

## Reproduced surfaces and repairs

| Surface | Constraint / expected repair | Coverage |
| --- | --- | --- |
| ADS-B selected aircraft and tracked list | 280/340px details cap and nested list scrollbar; details expand and list follows | Full selection, late details, shrink/deselect, focus, 16 layout combinations |
| Main mode workspace / sidebar / output | Viewport-height grid with internal scroll; page grows and sidebar controls stay reachable | Every registered mode with synthetic long output, standalone/embed, four viewports/themes |
| AIS selected vessel and lists | Selected vessel cap, bounded dashboard/sidebar | Populated detail regression |
| Satellite telemetry and pass list | Panel content max heights, scrolling drawer/list | Populated detail/list regressions; map canvas preserved |
| ISS sidebar | Locked page/side viewport | Populated sidebar regression |
| APRS stations | Nested station panel scrollbar | Populated station regression |
| Meshtastic and MeshCore dashboards | Viewport-height console, constrained side panels/tabs | Populated active detail regression |
| Weather satellite / SSTV / WEFAX | Capped pass/schedule/countdown/gallery information | Populated information regressions |
| Bluetooth / TSCM | Nested detail/detection lists | Populated synthetic contact/list regression |
| History / Messages / Controller monitor | Capped panel bodies and detail views | Populated detail regressions |
| Instruments / Controller manage | No capped visible information pane found in baseline | Existing page smoke, all layout setups |
| Settings / dialogs | One intentional viewport-bounded dialog scroll area | Long-dialog reachability check; nested information panes grow |

## Intentional bounded regions

Maps, spectra, radar canvases, image viewports, signal bars and decorative clipping retain explicit dimensions. They are graphical surfaces, not information cards. Their adjacent text and actions must remain in flow. Tables may scroll horizontally when their columns cannot fit a phone. Collapsed sections and inactive tabs remain explicitly user-controlled; layout rules must not reveal them.

Dialogs and the existing mobile navigation drawer retain a single viewport scroll area because they are overlays; their close controls and final actions must be reachable. No information-card cap is justified by a live-data source alone. Existing backend/UI retention limits and autoscroll behaviour are unchanged; historical data beyond those limits is outside this layout change.

## Final verification

Pending cross-mode regression matrix, full browser smoke and screenshot review. No deployment performed.
