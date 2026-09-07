from odoo import api, fields, models


class CustomerPOLine(models.Model):
    _name = "customer.po.line"
    _description = "Rincian Barang Form Purchase Order Customer"

    po_id = fields.Many2one(
        "customer.po",
        string="PO Reference",
        required=True,
        ondelete="cascade",
    )
    sequence = fields.Integer(string="Sequence", default=10)
    product_id = fields.Many2one(
        "product.product",
        string="Produk",
    )
    product_code = fields.Char(string="Kode Produk")
    name = fields.Text(string="Nama Produk / Deskripsi", required=True)
    product_qty = fields.Float(
        string="Qty",
        default=1.0,
        digits="Product Unit of Measure",
        required=True,
    )
    price_unit = fields.Monetary(
        string="Harga Satuan",
        required=True,
        currency_field="currency_id",
    )
    price_total = fields.Monetary(
        string="Jumlah Total",
        compute="_compute_price_total",
        store=True,
        currency_field="currency_id",
    )
    currency_id = fields.Many2one(
        "res.currency",
        related="po_id.currency_id",
        store=True,
        readonly=True,
    )

    @api.onchange("product_id")
    def _onchange_product_id(self):
        if self.product_id:
            self.product_code = self.product_id.default_code or ""
            self.name = self.product_id.display_name or self.product_id.name
            self.price_unit = self.product_id.lst_price or 0.0

    @api.depends("product_qty", "price_unit")
    def _compute_price_total(self):
        for line in self:
            line.price_total = line.product_qty * line.price_unit
