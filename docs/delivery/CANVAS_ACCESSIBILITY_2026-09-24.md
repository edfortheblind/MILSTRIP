# Canvas accessibility source update

Status: accessibility properties are verified in both saved native v2 drafts.
Keyboard and screen-reader acceptance remain pending. This evidence does not
establish publication or complete accessibility.

Both broker variants now contain:

- Accessible names for six text inputs, three dropdowns and four galleries.
- Item descriptions for request, record, audit and user galleries.
- `TabIndex = 0` and a three-pixel focus border on 46 interactive controls.
- `Live = Live.Polite` on each screen's status-message label.
- Contextual row-button text and the checkbox text `Enable database`.

The password field's accessible name is constant and contains no entered value.
Static labels retain their native `TabIndex = -1` default. Gallery containers
retain their default tab behavior; their action buttons are keyboard targets.
Button focus borders use the existing text color. Input and checkbox focus
borders are black. Final contrast and keyboard behavior require native review.

## Supported properties

Every added or changed property was checked against the template metadata in the
private Stage broker baseline export: Button 2.2.0, TextInput 2.3.2, DropDown
2.3.1, CheckBox 2.1.0, Gallery 2.15.0 and Label 2.5.1. The check covered 165
property changes per profile; no unsupported property was added.

Classic Button and CheckBox use `Text` for their accessible names. Their native
templates do not expose `AccessibleLabel`, so that property was not added to
them. This matches Microsoft's [Button](https://learn.microsoft.com/en-us/power-apps/maker/canvas-apps/controls/control-button)
and [CheckBox](https://learn.microsoft.com/en-us/power-apps/maker/canvas-apps/controls/control-check-box)
screen-reader guidance.

## Verification

Twenty focused Canvas and source-assembly tests passed after the subsequent
protected-Owner display and administration-message fixes. Regression checks
confirm unchanged control types, behavior expressions, data bindings, disabled
states and secret-field behavior. All six screen event definitions remain
explicit; the four business screens retain `OnVisible = false`.

Direct inspection of both September 24 native `admin-draft-v2.msapp` exports
confirmed all 679 generated control properties, including these accessibility
properties. Item descriptions reside on each native gallery template. Export
hashes and the separate parser-counter discrepancy are recorded in the
[native source evidence](CANVAS_SOURCE_ASSEMBLY_2026-09-24.md#current-native-evidence--september-24).

The earlier Studio count of 79 accessibility findings is now **66** in each
export: 27 focus-border findings on static labels, 35 tab-stop findings on those
labels plus four logos and four galleries, and four accessible-name findings on
the logos. Native labels and decorative images have `OnSelect=false` and
`TabIndex=-1`; the logos intentionally have empty accessible names. No extra
nonempty behavior handlers were found.

Keep static text and decorative logos out of the tab sequence. Those settings
match Microsoft's [accessibility property guidance](https://learn.microsoft.com/en-us/power-apps/maker/canvas-apps/controls/properties-accessibility).
The remaining static-control findings appear to classify inert controls as
interactive; that interpretation still needs runtime confirmation. Microsoft
also advises evaluating [checker suggestions in the app's context](https://learn.microsoft.com/en-us/power-apps/maker/canvas-apps/accessibility-checker).
Do not add dozens of keyboard stops merely to lower the count. Gallery selection
settings remain unchanged; the existing row buttons provide explicit actions.

Before accessibility acceptance, use Tab and Shift+Tab on every screen: headings
and logos should be skipped, enabled controls and row buttons should be reachable,
focus should be visible, and galleries must not trap the keyboard. Confirm that
Enter/Space activates an existing row button. With a screen reader, verify
content order, control names, result text and polite status announcements.
These native checks remain open; source matching alone cannot establish them.
