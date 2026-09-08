from odoo import api, fields, models
from datetime import timedelta


class CrmLead(models.Model):
    _inherit = "crm.lead"

    surat_penawaran_ids = fields.One2many(
        "surat.penawaran",
        "opportunity_id",
        string="Surat Penawaran",
    )
    surat_penawaran_count = fields.Integer(
        string="Jumlah Penawaran",
        compute="_compute_surat_penawaran_count",
    )
    customer_po_ids = fields.One2many(
        "customer.po",
        "opportunity_id",
        string="Purchase Order Customer",
    )
    customer_po_count = fields.Integer(
        string="Jumlah PO",
        compute="_compute_customer_po_count",
    )

    @api.depends("surat_penawaran_ids")
    def _compute_surat_penawaran_count(self):
        for lead in self:
            lead.surat_penawaran_count = len(lead.surat_penawaran_ids)

    @api.depends("customer_po_ids")
    def _compute_customer_po_count(self):
        for lead in self:
            lead.customer_po_count = len(lead.customer_po_ids)

    def _ensure_lead_partner(self):
        """Memastikan partner_id terisi dari instansi/lead jika masih kosong."""
        self.ensure_one()
        partner = self.partner_id
        if not partner:
            partner_name = (self.partner_name or self.name or "").strip()
            if partner_name:
                partner = self.env["res.partner"].search([("name", "=ilike", partner_name)], limit=1)
                if not partner:
                    partner = self.env["res.partner"].create({
                        "name": partner_name,
                        "phone": self.phone or False,
                        "mobile": self.mobile or False,
                        "email": self.email_from or False,
                        "street": self.street or False,
                        "street2": self.street2 or False,
                        "city": self.city or False,
                        "state_id": self.state_id.id if self.state_id else False,
                    })
                self.partner_id = partner.id
        return partner

    def action_create_surat_penawaran(self):
        """Tombol aksi langsung membuat Surat Penawaran dengan data otomatis dari Lead."""
        self.ensure_one()
        partner = self._ensure_lead_partner()
        today = fields.Date.context_today(self)
        validity = today + timedelta(days=30)
        return {
            "name": "Buat Surat Penawaran",
            "type": "ir.actions.act_window",
            "res_model": "surat.penawaran",
            "view_mode": "form",
            "target": "current",
            "context": {
                "default_opportunity_id": self.id,
                "default_partner_id": partner.id if partner else False,
                "default_user_id": self.env.user.id,
                "default_date_order": today,
                "default_validity_date": validity,
                "default_pic_name": self.contact_name or (partner.name if partner else ""),
                "default_pic_phone": self.mobile or self.phone or "",
                "default_pic_email": self.email_from or "",
                "default_pic_position": self.function or "",
            },
        }

    def action_create_customer_po(self):
        """Tombol aksi langsung membuat Form PO Customer dengan data otomatis dari Lead."""
        self.ensure_one()
        partner = self._ensure_lead_partner()
        return {
            "name": "Buat Form Purchase Order (PO)",
            "type": "ir.actions.act_window",
            "res_model": "customer.po",
            "view_mode": "form",
            "target": "current",
            "context": {
                "default_opportunity_id": self.id,
                "default_partner_id": partner.id if partner else False,
                "default_salesperson_id": self.env.user.id,
                "default_signer_name": self.contact_name or (partner.name if partner else ""),
                "default_signer_mobile": self.mobile or self.phone or "",
                "default_signer_email": self.email_from or "",
                "default_signer_job": self.function or "",
            },
        }

    def action_view_surat_penawaran(self):
        self.ensure_one()
        partner = self._ensure_lead_partner()
        action = self.env["ir.actions.actions"]._for_xml_id("agi_surat_penawaran.action_surat_penawaran")
        action["domain"] = [("opportunity_id", "=", self.id)]
        action["context"] = {
            "default_opportunity_id": self.id,
            "default_partner_id": partner.id if partner else False,
            "default_user_id": self.env.user.id,
            "default_pic_name": self.contact_name or (partner.name if partner else ""),
            "default_pic_phone": self.mobile or self.phone or "",
            "default_pic_email": self.email_from or "",
            "default_pic_position": self.function or "",
        }
        return action

    def action_view_customer_po(self):
        self.ensure_one()
        partner = self._ensure_lead_partner()
        action = self.env["ir.actions.actions"]._for_xml_id("agi_surat_penawaran.action_customer_po")
        action["domain"] = [("opportunity_id", "=", self.id)]
        action["context"] = {
            "default_opportunity_id": self.id,
            "default_partner_id": partner.id if partner else False,
            "default_salesperson_id": self.env.user.id,
            "default_signer_name": self.contact_name or (partner.name if partner else ""),
            "default_signer_mobile": self.mobile or self.phone or "",
            "default_signer_email": self.email_from or "",
            "default_signer_job": self.function or "",
        }
        return action
