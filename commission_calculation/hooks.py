# -*- coding: utf-8 -*-

import logging

_logger = logging.getLogger(__name__)


def pre_init_alter_table(cr):
    """This pre_init will create new columns in tables:
        - account_move_line: date_last_payment, rec_aml, rec_invoice
        - account_invoice: date_last_payment.
    After columns have been created constraints are added in table:
        - account_move_line: FOREIGN KEY rec_invoice & rec_aml"""

    _logger.info('Creating fields date_last_payment, rec_aml, rec_invoice '
                 'on account_move_line')
    cr.execute("""
        ALTER TABLE account_move_line
        ADD COLUMN date_last_payment date,
        ADD COLUMN rec_aml integer,
        ADD COLUMN rec_invoice integer;
    """)

    _logger.info('Creating fields date_last_payment on account_invoice')
    cr.execute("""
        ALTER TABLE account_invoice
        ADD COLUMN date_last_payment date;
    """)

    _logger.info('Creating Constraints for rec_aml, rec_invoice '
                 'on account_move_line')
    cr.execute("""
        ALTER TABLE account_move_line
        ADD CONSTRAINT account_move_line_rec_invoice_id_fkey
        FOREIGN KEY (rec_invoice)
        REFERENCES account_invoice(id)
        ON DELETE SET NULL,
        ADD CONSTRAINT account_move_line_rec_aml_id_fkey
        FOREIGN KEY (rec_aml)
        REFERENCES account_move_line(id)
        ON DELETE SET NULL;
    """)


def pre_init_update_table(cr):
    """This pre_init will update the newly created columns with appropriate
    values in the tables:
        - account_move_line: date_last_payment, rec_aml, rec_invoice
        - account_invoice: date_last_payment.
    This is done at this stage because in databases with existing data
    letting the python code do this procedure can become a time consuming
    process for computed fields with hungry resource methods.
        """
    _logger.info('Updating fields rec_aml on account_move_line')
    cr.execute("""
        UPDATE account_move_line aml1
        SET rec_aml = view.rec_aml
        FROM (
        SELECT
            aml.id AS rec_aml,
            cml.id AS aml_id
        FROM account_move_line aml
        INNER JOIN account_partial_reconcile apr ON apr.debit_move_id = aml.id
        INNER JOIN account_move_line cml ON apr.credit_move_id = cml.id
        INNER JOIN account_journal aj ON aj.id = cml.journal_id
        INNER JOIN account_account aa ON aa.id = aml.account_id
        WHERE aml.debit > 0
            AND aj.type IN ('bank', 'cash')
            AND aa.internal_type = 'receivable'
        ) AS view
        WHERE view.aml_id = aml1.id;
    """)

    _logger.info('Updating fields rec_invoice on account_move_line')
    cr.execute("""
        UPDATE account_move_line aml1
        SET rec_invoice = view.rec_invoice
        FROM (
        SELECT
            ai.id AS rec_invoice,
            cml.id AS aml_id
        FROM account_move_line aml
        INNER JOIN account_invoice ai ON ai.move_id = aml.move_id
        INNER JOIN account_partial_reconcile apr ON apr.debit_move_id = aml.id
        INNER JOIN account_move_line cml ON apr.credit_move_id = cml.id
        INNER JOIN account_journal aj ON aj.id = cml.journal_id
        INNER JOIN account_account aa ON aa.id = aml.account_id
        WHERE aml.debit > 0
            AND aj.type IN ('bank', 'cash')
            AND aa.internal_type = 'receivable'
        ) AS view
        WHERE view.aml_id = aml1.id;
    """)

    _logger.info('Updating fields date_last_payment on account_move_line')
    cr.execute("""
        UPDATE account_move_line aml1
        SET date_last_payment = view.date_last_payment
        FROM (
        SELECT
            aml.id AS aml_id,
            MAX(cml.date) as date_last_payment
        FROM account_move_line aml
        INNER JOIN account_partial_reconcile apr ON apr.debit_move_id = aml.id
        INNER JOIN account_move_line cml ON apr.credit_move_id = cml.id
        INNER JOIN account_journal aj ON aj.id = cml.journal_id
        INNER JOIN account_account aa ON aa.id = aml.account_id
        WHERE aml.debit > 0
            AND aj.type IN ('bank', 'cash')
            AND aa.internal_type = 'receivable'
        GROUP BY aml.id
        ) AS view
        WHERE view.aml_id = aml1.id;
    """)

    _logger.info('Updating fields date_last_payment on account_invoice')
    cr.execute("""
        UPDATE account_invoice ai1
        SET date_last_payment = view.date_last_payment
        FROM (
        SELECT
            ai.id AS invoice_id,
            MAX(cml.date) as date_last_payment
        FROM account_invoice ai
        INNER JOIN account_move_line aml ON ai.move_id = aml.move_id
        INNER JOIN account_partial_reconcile apr ON apr.debit_move_id = aml.id
        INNER JOIN account_move_line cml ON apr.credit_move_id = cml.id
        INNER JOIN account_journal aj ON aj.id = cml.journal_id
        INNER JOIN account_account aa ON aa.id = aml.account_id
        WHERE aml.debit > 0
            AND aj.type IN ('bank', 'cash')
            AND aa.internal_type = 'receivable'
        GROUP BY ai.id
        ) AS view
        WHERE view.invoice_id = ai1.id;
    """)


def pre_init_hook(cr):
    """This pre_init_hook will create new columns on the existing tables and
    will populate them with appropriate data so that installing this module in
    database with huge amount of Entry Lines or Invoices do not become into
    painful update"""
    pre_init_alter_table(cr)
    pre_init_update_table(cr)
