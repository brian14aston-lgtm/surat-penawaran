from odoo import api, fields, models


class SuratPenawaranLine(models.Model):
    _name = "surat.penawaran.line"
    _description = "Surat Penawaran Line"
    _order = "sequence, id"

    surat_id = fields.Many2one(
        "surat.penawaran",
        string="Surat Penawaran",
        required=True,
        ondelete="cascade",
    )
    currency_id = fields.Many2one(
        "res.currency",
        related="surat_id.currency_id",
        string="Currency",
        readonly=True,
        store=True,
    )
    sequence = fields.Integer(string="No.", default=10)
    product_id = fields.Many2one("product.product", string="Produk", required=True)
    name = fields.Text(string="Deskripsi", required=True)
    product_uom_qty = fields.Float(string="Qty", required=True, default=1.0, digits="Product Unit of Measure")
    product_uom = fields.Many2one(
        "uom.uom",
        string="Satuan",
        related="product_id.uom_id",
        readonly=True,
        store=True,
    )
    unit_price = fields.Monetary(
        string="Harga Satuan",
        required=True,
        currency_field="currency_id",
    )
    discount = fields.Float(string="Diskon (%)", default=0.0, digits="Discount")
    tax_ids = fields.Many2many(
        "account.tax",
        string="Pajak",
        domain="[('type_tax_use','=','sale')]",
    )
    price_subtotal = fields.Monetary(
        string="Subtotal",
        compute="_compute_price",
        store=True,
        currency_field="currency_id",
    )
    price_tax = fields.Monetary(
        string="Jumlah Pajak",
        compute="_compute_price",
        store=True,
        currency_field="currency_id",
    )
    price_total = fields.Monetary(
        string="Total",
        compute="_compute_price",
        store=True,
        currency_field="currency_id",
    )

    @api.depends("product_uom_qty", "unit_price", "discount", "tax_ids", "surat_id.currency_id")
    def _compute_price(self):
        for line in self:
            price = line.unit_price * (1 - (line.discount or 0.0) / 100.0)
            currency = line.surat_id.currency_id or line.surat_id.company_id.currency_id
            taxes = line.tax_ids.compute_all(
                price,
                currency=currency,
                quantity=line.product_uom_qty,
                product=line.product_id,
                partner=line.surat_id.partner_id,
            )
            line.price_subtotal = taxes["total_excluded"]
            line.price_tax = taxes["total_included"] - taxes["total_excluded"]
            line.price_total = taxes["total_included"]

    @api.onchange("product_id")
    def _onchange_product_id(self):
        if self.product_id:
            self.name = self.product_id.get_product_multiline_description_sale()
            self.unit_price = self.product_id.list_price
            if self.product_id.taxes_id:
                company = self.surat_id.company_id or self.env.company
                self.tax_ids = self.product_id.taxes_id.filtered(lambda t: t.company_id == company)

