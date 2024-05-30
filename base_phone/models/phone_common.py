# Copyright 2010-2021 Akretion France (http://www.akretion.com/)
# @author: Alexis de Lattre <alexis.delattre@akretion.com>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

import logging

from odoo import api, models

_logger = logging.getLogger(__name__)

try:
    import phonenumbers
except ImportError:
    _logger.debug("Cannot `import phonenumbers`.")

_PHONEMODEL_ADDITIONAL_WHERE_CLAUSE = {
    'res.partner': """
        or id in (
            select partner
            from partner_multi_phone_phone
            where val ilike %(pg_search_number)s
        )
    """
}


class PhoneCommon(models.AbstractModel):
    _name = "phone.common"
    _description = "Common methods for phone features"

    @api.model
    def get_name_from_phone_number(self, presented_number):
        """Function to get name from phone number. Usefull for use from IPBX
        to add CallerID name to incoming calls."""
        res = self.get_record_from_phone_number(presented_number)
        if res:
            return res[2]
        else:
            return False

    @api.model
    def get_record_from_phone_number(self, presented_number):
        """If it finds something, it returns (object name, ID, record name)
        For example : ('res.partner', 42, 'Alexis de Lattre (Akretion)')
        """
        _logger.debug(
            "Call get_name_from_phone_number with number = %s" % presented_number
        )
        if not isinstance(presented_number, str):
            _logger.warning(
                f"Number {presented_number} should be a 'str' but it is a"
                f" {type(presented_number)}"
            )
            return False
        if not presented_number.isdigit():
            _logger.warning(
                "Number '%s' should only contain digits." % presented_number
            )

        nr_digits_to_match_from_end = (
            self.env.company.number_of_digits_to_match_from_end
        )
        if len(presented_number) >= nr_digits_to_match_from_end:
            end_number_to_match = presented_number[
                -nr_digits_to_match_from_end : len(presented_number)
            ]
        else:
            end_number_to_match = presented_number

        sorted_phonemodels = self._get_phone_models()
        rtr = []
        for obj_dict in sorted_phonemodels:
            obj = obj_dict["object"]
            obj_name = obj._name
            pg_search_number = "%" + end_number_to_match
            _logger.debug(
                "Will search phone and mobile numbers in %s ending with '%s'",
                obj_name,
                end_number_to_match,
            )
            sql_where = []
            for field in obj_dict["fields"]:
                sql_where.append(f"replace({field}, ' ', '') ilike %(pg_search_number)s")
            sql = (
                "select id, {rec_name}"
                " from {tbl_name} where ({where_clause})"
            ).format(
                rec_name=obj._rec_name,
                # string_of_phone_fields=', '.join(obj_dict["fields"]) + ' ',
                tbl_name=obj._table,
                where_clause=" or ".join(sql_where)
            ) + _PHONEMODEL_ADDITIONAL_WHERE_CLAUSE.get(obj_name, '')
            sql_args = {'pg_search_number': f'%{pg_search_number}'}
            _logger.debug(
                "get_record_from_phone_number sql=%s sql_args=%s", sql, sql_args
            )
            self._cr.execute(sql, sql_args)
            res_sql = self._cr.dictfetchall()
            if res_sql:
                rtr += [(
                    obj_name,
                    rec['id'],
                    rec['name'],
                ) for rec in res_sql]
            else:
                _logger.debug(
                    "No match on %s for end of phone number '%s'",
                    obj_name,
                    end_number_to_match,
                )

        return rtr, presented_number

    @api.model
    def _get_phone_models(self):
        return [  # i don't see the reason to run all this code and add all this complexity for something so static
            {'fields': ['phone', 'mobile'], 'object': self.with_context(callerid=True).env['res.partner']},
            {'fields': ['phone', 'mobile'], 'object': self.with_context(callerid=True).env['crm.lead']},
        ]

    @api.model
    def click2dial(self, erp_number):
        """This function is designed to be overridden in IPBX-specific
        modules, such as asterisk_click2dial or ovh_telephony_connector"""
        return {"dialed_number": erp_number}

    @api.model
    def convert_to_dial_number(self, erp_number):
        """
        This function is dedicated to the transformation of the number
        available in Odoo to the number that can be dialed.
        You may have to inherit this function in another module specific
        for your company if you are not happy with the way I reformat
        the numbers.
        """
        assert erp_number, "Missing phone number"
        _logger.debug("Number before reformat = %s" % erp_number)
        # erp_number are supposed to be in International format, so no need to
        # give a country code here
        try:
            parsed_num = phonenumbers.parse(erp_number, None)
        except NameError:
            return erp_number
        country_code = self.env.company.country_id.code
        assert country_code, "Missing country on company"
        _logger.debug("Country code = %s" % country_code)
        to_dial_number = phonenumbers.format_out_of_country_calling_number(
            parsed_num, country_code.upper()
        )
        to_dial_number = to_dial_number.translate(
            to_dial_number.maketrans("", "", " -.()/")
        )
        _logger.debug("Number to be sent to phone system: %s" % to_dial_number)
        return to_dial_number
