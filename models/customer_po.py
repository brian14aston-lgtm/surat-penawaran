from odoo import api, fields, models
from odoo.exceptions import ValidationError


class CustomerPO(models.Model):
    _name = "customer.po"
    _description = "Form Purchase Order Customer"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _order = "date_order desc, name desc"

    name = fields.Char(
        string="Nomor PO",
        required=False,
        copy=False,
        readonly=False,
        default="",
        tracking=True,
    )
    place = fields.Char(
        string="Tempat",
        tracking=True,
    )
    date_order = fields.Date(
        string="Tanggal PO",
        default=fields.Date.context_today,
        required=True,
        tracking=True,
    )

    # Vendor Info (PT. Aston Graphindo Indonesia or company)
    company_id = fields.Many2one(
        "res.company",
        string="Perusahaan Penerima PO",
        required=True,
        default=lambda self: self.env.company,
    )
    currency_id = fields.Many2one(
        "res.currency",
        related="company_id.currency_id",
        string="Currency",
        store=True,
        readonly=True,
    )

    # Pemesan / Bertandatangan di bawah ini
    signer_name = fields.Char(string="Nama Lengkap Penandatangan", required=True, tracking=True)
    signer_job = fields.Char(string="Jabatan", tracking=True)
    signer_mobile = fields.Char(string="No. Handphone", tracking=True)
    signer_email = fields.Char(string="Alamat E-mail", tracking=True)

    # Instansi / Tempat Bekerja
    partner_id = fields.Many2one(
        "res.partner",
        string="Instansi / Customer",
        required=True,
        tracking=True,
    )
    instansi_name = fields.Char(string="Nama Instansi", tracking=True)
    instansi_address = fields.Text(string="Alamat Instansi", tracking=True)
    instansi_phone = fields.Char(string="Nomer Telepon Instansi", tracking=True)

    @api.onchange("partner_id")
    def _onchange_partner_id(self):
        if self.partner_id:
            self.instansi_name = self.partner_id.name
            address_parts = [
                self.partner_id.street,
                self.partner_id.street2,
                self.partner_id.city,
                self.partner_id.state_id.name if self.partner_id.state_id else "",
                self.partner_id.zip,
            ]
            self.instansi_address = ", ".join([p for p in address_parts if p])
            self.instansi_phone = self.partner_id.phone or self.partner_id.mobile or ""
            self.place = self.partner_id.city or (self.partner_id.state_id.name if self.partner_id.state_id else "")

    # Ketentuan & Syarat
    payment_term_desc = fields.Char(
        string="Pelunasan Pembayaran",
        default="30 Hari terhitung sejak barang diterima",
    )
    payment_due_date = fields.Date(string="Tanggal Jatuh Tempo")
    transaction_method = fields.Char(
        string="Metode Transaksi",
        default="Pembelian Langsung",
    )

    # Checkbox Include Tax & Shipping
    include_ppn = fields.Boolean(string="Include PPN", default=True)
    include_pph = fields.Boolean(string="Include PPH", default=False)
    include_shipping = fields.Boolean(string="Include Biaya Kirim", default=True)

    court_domicile = fields.Char(
        string="Domisili Hukum Pengadilan",
        default="Pengadilan Negeri Karanganyar",
    )
    notes_other = fields.Text(string="Lainnya")

    # Signatures Info
    salesperson_id = fields.Many2one(
        "res.users",
        string="Salesman (Penerima Pesanan)",
        default=lambda self: self.env.user,
        tracking=True,
    )
    salesperson_name = fields.Char(string="Nama Salesman")
    approver_name = fields.Char(
        string="Pesanan Disetujui Oleh (PT. Aston Graphindo Indonesia)",
        default="Febriyan Adi Garuda Sakti",
    )

    @api.onchange("salesperson_id")
    def _onchange_salesperson_id(self):
        if self.salesperson_id:
            self.salesperson_name = self.salesperson_id.name

    # Lines
    line_ids = fields.One2many(
        "customer.po.line",
        "po_id",
        string="Rincian Barang",
        copy=True,
    )

    # Totals
    amount_total = fields.Monetary(
        string="Total",
        compute="_compute_amount_total",
        store=True,
        currency_field="currency_id",
        tracking=True,
    )
    amount_total_words = fields.Char(
        string="Terbilang",
        compute="_compute_amount_total_words",
        store=True,
    )

    state = fields.Selection(
        [
            ("draft", "Draft"),
            ("confirmed", "Disetujui / Confirmed"),
            ("cancel", "Batal"),
        ],
        string="Status",
        default="draft",
        tracking=True,
        copy=False,
    )

    @api.depends("line_ids.price_total")
    def _compute_amount_total(self):
        for rec in self:
            rec.amount_total = sum(rec.line_ids.mapped("price_total"))

    @api.depends("amount_total", "currency_id")
    def _compute_amount_total_words(self):
        for rec in self:
            if rec.amount_total:
                words = rec.currency_id.with_context(lang="id_ID").amount_to_text(rec.amount_total) if rec.currency_id else ""
                if not words or "Rupiah" not in words:
                    # Fallback Bahasa Indonesia terbilang sederhana
                    words = rec._amount_to_text_id(rec.amount_total)
                rec.amount_total_words = words
            else:
                rec.amount_total_words = ""

    def _amount_to_text_id(self, amount):
        units = ["", "Satu", "Dua", "Tiga", "Empat", "Lima", "Enam", "Tujuh", "Delapan", "Sembilan", "Sepuluh", "Sebelas"]
        def _say(n):
            if n < 12:
                return units[int(n)]
            elif n < 20:
                return _say(n - 10) + " Belas"
            elif n < 100:
                return _say(n // 10) + " Puluh " + _say(n % 10)
            elif n < 200:
                return "Seratus " + _say(n - 100)
            elif n < 1000:
                return _say(n // 100) + " Ratus " + _say(n % 100)
            elif n < 2000:
                return "Seribu " + _say(n - 1000)
            elif n < 1000000:
                return _say(n // 1000) + " Ribu " + _say(n % 1000)
            elif n < 1000000000:
                return _say(n // 1000000) + " Juta " + _say(n % 1000000)
            elif n < 1000000000000:
                return _say(n // 1000000000) + " Miliar " + _say(n % 1000000000)
            return str(n)
        
        val = int(round(amount))
        res = _say(val).strip()
        import re
        res = re.sub(r"\s+", " ", res)
        return res + " Rupiah"

    @api.model
    def create(self, vals):
        # Allow blank name for manual customer filling
        return super(CustomerPO, self).create(vals)

    def action_print(self):
        return self.env.ref("agi_surat_penawaran.action_report_customer_po").report_action(self)

    def action_confirm(self):
        self.write({"state": "confirmed"})

    def action_cancel(self):
        self.write({"state": "cancel"})

    def action_draft(self):
        self.write({"state": "draft"})
