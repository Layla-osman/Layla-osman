odoo.define('point_of_sale.GiftScreen', function (require) {
    'use strict';

    const ReceiptScreen = require('point_of_sale.ReceiptScreen');
    const Registries = require('point_of_sale.Registries');
    const GiftScreen = (ReceiptScreen) =>
        class extends ReceiptScreen {
            constructor() {
                super(...arguments);
                this.is_gift = false;
                this.is_arabic = false;
            }
            giftTemplate() {
                this.is_gift = true;
                this.is_arabic = false;
                this.render();
            }
            arabicTemplate(){
                this.is_arabic = true;
                this.is_gift = false;
                this.render();
            }
        };
    Registries.Component.extend(ReceiptScreen, GiftScreen);
    return ReceiptScreen;
});