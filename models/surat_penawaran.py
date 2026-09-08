from odoo import api, fields, models
from odoo.exceptions import ValidationError


class SuratPenawaran(models.Model):
    _name = "surat.penawaran"
    _description = "Surat Penawaran"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _order = "date_order desc, name desc"

    name = fields.Char(
        string="Nomor Surat",
        required=True,
        copy=False,
        readonly=True,
        default="New",
        tracking=True,
    )
    partner_id = fields.Many2one(
        "res.partner",
        string="Customer",
        required=True,
        tracking=True,
    )
    opportunity_id = fields.Many2one(
        "crm.lead",
        string="Peluang / CRM Lead",
        tracking=True,
        help="Lead / Opportunity yang terkait dengan surat penawaran ini.",
    )
    user_id = fields.Many2one(
        "res.users",
        string="Salesperson",
        default=lambda self: self.env.user,
        tracking=True,
    )
    date_order = fields.Date(
        string="Tanggal Surat",
        default=fields.Date.context_today,
        required=True,
        tracking=True,
    )
    validity_date = fields.Date(
        string="Berlaku Sampai",
        tracking=True,
    )
    state = fields.Selection(
        [
            ("draft", "Draft"),
            ("sent", "Terkirim"),
            ("accepted", "Diterima"),
            ("refused", "Ditolak"),
        ],
        string="Status",
        default="draft",
        tracking=True,
        copy=False,
    )
    pic_name = fields.Char(string="Nama PIC", required=True, tracking=True)
    pic_position = fields.Char(string="Jabatan PIC", tracking=True)
    pic_email = fields.Char(string="Email PIC", tracking=True)
    pic_phone = fields.Char(string="No. HP PIC", tracking=True)
    notes = fields.Text(
        string="Catatan / Syarat & Ketentuan",
        default="1. Harga sudah termasuk PPN (jika ada).\n2. Pembayaran ditransfer ke rekening resmi perusahaan.\n3. Masa berlaku penawaran sesuai dengan tanggal yang tertera.",
    )
    line_ids = fields.One2many(
        "surat.penawaran.line",
        "surat_id",
        string="Detail Produk",
        copy=True,
    )
    company_id = fields.Many2one(
        "res.company",
        string="Company",
        required=True,
        default=lambda self: self.env.company,
    )
    currency_id = fields.Many2one(
        "res.currency",
        string="Currency",
        default=lambda self: self.env.company.currency_id,
        required=True,
    )
    amount_untaxed = fields.Monetary(
        string="Total Sebelum Pajak",
        compute="_compute_amounts",
        store=True,
        currency_field="currency_id",
        tracking=True,
    )
    amount_tax = fields.Monetary(
        string="Pajak",
        compute="_compute_amounts",
        store=True,
        currency_field="currency_id",
    )
    amount_total = fields.Monetary(
        string="Total",
        compute="_compute_amounts",
        store=True,
        currency_field="currency_id",
        tracking=True,
    )

    @api.onchange("partner_id")
    def _onchange_partner_id(self):
        if self.partner_id:
            contact = self.partner_id.child_ids.filtered(lambda c: c.type == "contact")[:1]
            target = contact or self.partner_id

            self.pic_name = target.name or self.partner_id.name or ""
            self.pic_position = target.function or ""
            self.pic_email = target.email or self.partner_id.email or ""
            self.pic_phone = target.mobile or target.phone or self.partner_id.mobile or self.partner_id.phone or ""

    @api.depends("line_ids.price_subtotal", "line_ids.price_tax")
    def _compute_amounts(self):
        for rec in self:
            rec.amount_untaxed = sum(rec.line_ids.mapped("price_subtotal"))
            rec.amount_tax = sum(rec.line_ids.mapped("price_tax"))
            rec.amount_total = rec.amount_untaxed + rec.amount_tax

    def _trigger_crm_p2(self):
        """Otomatis memicu perpindahan lead ke stage P2 (Interest) jika ada penawaran."""
        p2_stage = self.env["crm.stage"].search([
            "|",
            ("name", "ilike", "P2"),
            ("name", "ilike", "Interest")
        ], limit=1)
        for rec in self:
            lead = rec.opportunity_id
            if not lead and rec.partner_id:
                lead = self.env["crm.lead"].search([
                    ("partner_id", "=", rec.partner_id.id),
                    ("type", "=", "opportunity"),
                    ("probability", "<", 100),
                ], limit=1)
                if lead:
                    rec.opportunity_id = lead.id

            if lead and p2_stage:
                current_stage_name = lead.stage_id.name or ""
                if "P0" not in current_stage_name and "P1" not in current_stage_name:
                    if lead.stage_id.id != p2_stage.id:
                        lead.stage_id = p2_stage.id
                        lead.message_post(
                            body=f"⚡ **Otomatis Naik ke P2 (Interest)** karena Surat Penawaran resmi **{rec.name}** telah diterbitkan untuk {rec.partner_id.name} (Total: {rec.currency_id.symbol or 'Rp'} {rec.amount_total:,.2f})."
                        )
                if not lead.expected_revenue or lead.expected_revenue == 0:
                    lead.expected_revenue = rec.amount_total

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get("name", "New") == "New":
                vals["name"] = self.env["ir.sequence"].next_by_code("surat.penawaran") or "New"
        records = super().create(vals_list)
        for rec in records:
            rec._trigger_crm_p2()
        return records

    def unlink(self):
        for rec in self:
            if rec.state not in ("draft",):
                raise ValidationError("Anda hanya dapat menghapus Surat Penawaran dengan status Draft.")
        return super().unlink()

    def action_send(self):
        for rec in self:
            rec.write({"state": "sent"})
            rec.message_post(body="Status diubah menjadi **Terkirim**.")
            rec._trigger_crm_p2()

    def action_accept(self):
        for rec in self:
            rec.write({"state": "accepted"})
            rec.message_post(body="Status diubah menjadi **Diterima**.")
            rec._trigger_crm_p2()

    def action_refuse(self):
        for rec in self:
            rec.write({"state": "refused"})
            rec.message_post(body="Status diubah menjadi **Ditolak**.")

    def action_reset_to_draft(self):
        for rec in self:
            rec.write({"state": "draft"})
            rec.message_post(body="Surat Penawaran direset kembali ke **Draft**.")

    def action_print(self):
        self.ensure_one()
        self._trigger_crm_p2()
        return self.env.ref("agi_surat_penawaran.action_report_surat_penawaran").report_action(self)

    @api.constrains("validity_date", "date_order")
    def _check_dates(self):
        for rec in self:
            if rec.validity_date and rec.date_order and rec.validity_date < rec.date_order:
                raise ValidationError("Tanggal 'Berlaku Sampai' tidak boleh lebih awal dari Tanggal Surat.")

