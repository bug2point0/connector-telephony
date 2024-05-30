/** @odoo-module **/

/*
    Copyright 2024 Dixmit
    License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
*/

import {Component} from "@odoo/owl";
import {_t} from "@web/core/l10n/translation";
import {registry} from "@web/core/registry";
import {useService} from "@web/core/utils/hooks";
import { Dialog } from "@web/core/dialog/dialog";
const systrayRegistry = registry.category("systray");

export class CallersDialog extends Component {}
CallersDialog.template = "asterisk_click2dial.Click2DialCallers";
CallersDialog.components = { Dialog };
CallersDialog.props = {
    close: Function,
    title: { type: String, optional: true},
    talking_number: { type: String, optional: true},
    recs: { type: Object, optional: true },

};

export class Click2DialSystray extends Component {
    setup() {
        this.rpc = useService("rpc");
        this.action = useService("action");
        this.notification = useService("notification");
        this.user = useService("user");
        this.dialog = useService("dialog");
    }

    async onOpenCaller() {
        // Var session = require('web.session');

        const r = await this.rpc("/asterisk_click2dial/get_record_from_my_channel", {
            context: this.user.context,
        });
        if (r === false) {
            this.notification.add(
                _t(
                    "Calling party number not retreived from IPBX or IPBX unreachable by Odoo"
                ),
                {
                    title: _t("IPBX error"),
                }
            );
        } else if (typeof r === "string" && isNaN(r)) {
            this.notification.add(_t("The calling number is not a phone number!"), {
                title: r,
            });
        }  else if (((typeof r === "string")) || (typeof r === "object" && !(r.length === 0))) {
            let rarr = r[0];
            for (let index = 0; index < rarr.length; ++index) {
                rarr[index][3] = '/web#id=' + rarr[index][1] + '&model=' + rarr[index][0] + '&view_type=form&cids=1'

                // ...use `element`...
            }
            this.dialog.add(CallersDialog, {
                recs: rarr,
                title: 'Με ποιόν συνομιλείς',
                talking_number: r[1],
            });
        }
    }
}

Click2DialSystray.template = "asterisk_click2dial.Click2DialSystray";

export const systrayItem = {Component: Click2DialSystray};

systrayRegistry.add("asterisk_click2dial.Click2DialSystray", systrayItem, {
    sequence: 99,
});
