odoo.define('pos_receipt_changes.changes', function (require) {
"use strict";

    var models = require('point_of_sale.models');
    var utils = require('web.utils');
    var round_pr = utils.round_precision;
    var core = require('web.core');
    var QWeb = core.qweb;
    var _t = core._t;

    // models.PosModel = models.PosModel.extend({
    //     this.session_name  = this.pos_session.name
    // });

    models.Orderline = models.Orderline.extend({
        get_price_before_discount: function() {
            return (this.get_unit_price() * this.get_quantity()).toFixed(this.pos.currency.decimals);
        },
        get_discount_amount: function() {
            return (this.get_unit_price() * this.get_quantity() * this.get_discount() / 100).toFixed(this.pos.currency.decimals);
        },
        get_price_after_discount: function() {
            return this.get_display_price().toFixed(this.pos.currency.decimals);
        },
    });
    models.Order = models.Order.extend({
        get_total_before_discount: function() {
            var result = 0.0;
            this.orderlines.forEach(function(orderLine,j) {
                result += Number(orderLine.get_price_before_discount());
            });
            return result.toFixed(this.pos.currency.decimals);
        },

    });

});