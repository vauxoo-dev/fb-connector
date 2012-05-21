from osv import osv, fields
import pooler
import time
import math
import mx.DateTime

from tools import config
from tools.translate import _
import decimal_precision as dp



class commission_payment(osv.osv):
    """
    OpenERP Model : commission_payment
    """
    
    _name = 'commission.payment'
    _description = __doc__
    
    _columns = {
        'name':fields.char('Concepto de Comisiones', size=256, required=True, readonly= True, states={'draft':[('readonly',False)]}),
        'bar_id': fields.many2one('baremo.book', 'Baremo', required=True, readonly= True, states={'draft':[('readonly',False)]}),
        'date_start':fields.date('Desde', required=True, readonly= True, states={'draft':[('readonly',False)]}),
        'date_stop':fields.date('Hasta', required=True, readonly= True, states={'draft':[('readonly',False)]}),
        'total_comm':fields.float('Total a Pagar', digits_compute=dp.get_precision('Commission'), readonly= True,states={'write':[('readonly',False)]}),
        'ret_notes':fields.text('Notas para las Retenciones',readonly= True, states={'draft':[('readonly',False)], 'open':[('readonly',False)]}),
        'uninvoiced_ids':fields.one2many('commission.uninvoiced', 'commission_id', 'Transacciones sin Facturas', readonly= True, states={'write':[('readonly',False)]}),
        'sale_noids':fields.one2many('commission.sale.noid', 'commission_id', 'Articulos sin asociacion', readonly= True, states={'write':[('readonly',False)]}),
        'noprice_ids':fields.one2many('commission.noprice', 'commission_id', 'Productos sin precio de lista historico', readonly= True, states={'write':[('readonly',False)]}),
        'comm_line_ids':fields.one2many('commission.lines', 'commission_id', 'Comision por productos', readonly= True, states={'write':[('readonly',False)]}),
        'saleman_ids':fields.one2many('commission.saleman', 'commission_id', 'Total de Comisiones por Vendedor', readonly= True, states={'write':[('readonly',False)]}),
        'user_ids': fields.many2many('res.users','commission_users','commission_id', 'user_id', 'Vendedores', required=True, readonly= True, states={'draft':[('readonly',False)]}),
        'voucher_ids': fields.many2many('account.voucher','commission_account_voucher','commission_id', 'voucher_id', 'Vouchers', readonly= True, states={'draft':[('readonly',False)],'open':[('readonly',False)],}),
        'comm_voucher_ids':fields.one2many('commission.voucher', 'commission_id', 'Vouchers afectados en esta comision', readonly= True, states={'write':[('readonly',False)]}),
        'comm_invoice_ids':fields.one2many('commission.invoice', 'commission_id', 'Facturas afectadas en esta comision', readonly= True, states={'write':[('readonly',False)]}),
        'comm_retention_ids':fields.one2many('commission.retention', 'commission_id', 'Facturas con Problemas de Retencion', readonly= True, states={'write':[('readonly',False)]}),
        'state': fields.selection([
            ('draft','Inicial'),
            ('open','En Proceso'),
            ('decide','Decidir'),
            ('write','Escribiendo'),
            ('done','Listo'),
            ('cancel','Cancelado')
        ],'Estado', readonly=True),
    }
    _defaults = {
        'name': lambda *a: None,
        'total_comm': lambda *a: 0.00,
        'state': lambda *a: 'draft',
        'ret_notes': lambda *a: 'Las Facturas que se mencionan ya tienen un pago registrado, pero presentan problemas con una o mas de las retenciones que se indican en el cuadro, se ha tratado bajo los medios existentes de identificar cuales son los porcentajes de retenciones pero no ha sido posible, para generar la comision sobre el pago de las mismas, es necesario el conocimiento de estos valores, por lo que le increpamos a que contacte a sus asociados para obtener esta informacion, su falta no afectara el calculo de la comision pero retardara su ejecucion. Si considera que ha habido un error por favor hable sobre el tema con el personal Administrativo y de Sistemas para determinar las causas del mismo y encontrar una solucion. De otra forma haga caso omiso de este mensaje y su contenido',
    }

    def prepare(self, cr, user, ids, context={}):
        """
        Este metodo recorre los elementos de account_voucher y verifica al menos 
        tres (3) caracteristicas primordiales para continuar con los vouchers:
        estas caracteristicas son: 
        - bank_rec_voucher: quiere decir que el voucher es de un deposito bancario
        (aqui aun no se ha considerado el trato que se le da a los cheques devueltos).
        - posted: quiere decir que el voucher ya se ha contabilizado, 
        condicion necesaria pero no suficiente.
        - move_ids: si la longitud de estos es distinto de cero es porque este voucher es
        por completo valido, es decir, realmente tiene asientos contables registrados.
        
        Si estas tres (3) condiciones se cumplen entonces se puede proceder a realizar la revision
        de las lineas de pago.
        
        
        @param cr: cursor to database
        @param user: id of current user
        @param ids: list of record ids to be process
        @param context: context arguments, like lang, time zone
        
        @return: return a result
        """
        
        self.write(cr, user, ids, {
                'state': 'open',
            })
        
        #~ Consultas
        accounts = self.pool.get('account.account')
        vouchers = self.pool.get('account.voucher')
        payments = self.pool.get ('account.voucher.line')
        invoices = self.pool.get ('account.invoice')
        invoice_lines = self.pool.get ('account.invoice.line')
        prod_prices = self.pool.get ('product.historic.price')
        partner_ids = self.pool.get ('res.partner')
        
        #~ Elementos Internos
        uninvoiced_pays = self.pool.get ('commission.uninvoiced')
        sale_noids = self.pool.get ('commission.sale.noid')
        noprice_ids = self.pool.get ('commission.noprice')
        comm_line_ids = self.pool.get ('commission.lines')
        saleman_ids = self.pool.get ('commission.saleman')
        #~ users_ids = self.pool.get ('commission.users')
        comm_voucher_ids = self.pool.get ('commission.voucher')
        comm_invoice_ids = self.pool.get ('commission.invoice')
        comm_retention_ids = self.pool.get ('commission.retention')
        
        ## Retenciones
        # de IVA
        ret_iva_lines = self.pool.get ('account.wh.iva.line')
        # de ISLR
        ret_islr_lines = self.pool.get ('islr.wh.doc.line')
        # de IM
        ret_im_lines = self.pool.get ('account.wh.munici.line')
        
        #commissions = self.pool.get('commission.payment')
        commissions = self.browse(cr, user, ids, context=None)
        
        for commission in commissions:
            # Desvincular lineas existentes, si las hubiere
            self.unlink(cr, user, ids, context=None)            
            
            date_start = commission.date_start
            date_stop = commission.date_stop
            
            #~ Obtener la lista de asesores/vendedores a los cuales se les hara el calculo de comisiones
            user_ids = []
            user_ids = [line.id for line in commission.user_ids]
            
            #~ Obtener la lista de vouchers que se seleccionaron manualmente en el widget many2many
            voucher_ids = []
            voucher_ids = [line.id for line in commission.voucher_ids]
            
            #~ Aqui verificamos que si no hay ningun voucher nosotros nos encargaremos de hacer la lista
            if not voucher_ids:
                # En esta busqueda restringimos que el voucher se haya contabilizado y que 
                # sea un cobro bancario y este dentro de la fecha estipulada
                voucher_ids = vouchers.search(cr, user, [('state', '=', 'posted'), ('type', '=', 'receipt'),('date', '>=', date_start),('date', '<=', date_stop)])
                
                commission.write({
                                'voucher_ids': [(6, commission.id, voucher_ids)],
                                },context=None) 
                                
            for vid in voucher_ids:
                    pay = vouchers.read(cr,user,vid,['name', 'date', 'amount', 'line_cr_ids','move_ids'],context=None)
                    if len(pay['move_ids'])!=0 and len(pay['line_cr_ids'])!=0:
                        # Con la negacion de esta condicion se termina de realizar la revision de las lineas de pago que cumplen con las tres
                        # condiciones estipuladas inicialmente, ahora se debe proseguir con la revision de las lineas de pago
                        print 'entre al if 1'
                        for pid in pay['line_cr_ids']:
                            print 'entre al for 1',pid
                            payment_brw = payments.browse(cr, user, pid, context=None)
                            pay_line_vendor = payment_brw.partner_id.user_id and payment_brw.partner_id.user_id.id or False
                            if pay_line_vendor in user_ids:
                                print 'entre al if 2'
                                # Leer cada una de las lineas de los vouchers
                                pay_line = payments.read(cr,user,pid,['name', 'invoice_id', 'amount', 'account_id', 'paid_comm'],context=None)
                                
                                
                                # Verificar si esta linea tiene factura y la comision del pago no se ha pagado
                                if (pay_line['invoice_id']!=False and pay_line['paid_comm']==False):
                                    print 'entre al if 3'
                                    # Si esta aqui dentro es porque esta linea tiene una id valida de una factura.
                                    inv_id = pay_line['invoice_id'][0]
                                    inv = invoices.read(cr,user,inv_id,['number', 'amount_untaxed', 'amount_total', 'invoice_line', 'date_invoice', 'partner_id'],context=None)
                                    
                                    # Obtener % IVA 
                                    perc_iva = round(((  inv['amount_total'] /  inv['amount_untaxed'])-1)*100,0)
                                    #~ print 'perc_iva: ',perc_iva,'\n'
                                    
                                    # Obtener el Valor de Porcentaje Retencion de esta factura
                                    
                                    # Las maneras faciles son las dos primeras que el cliente no retenga y la factura sea solo de productos
                                    # por lo que las retenciones de islr y im no aplican
                                    # o que el cliente retenga el 100% (algo poco visto) y sea una factura de productos
                                    no_ret_iva = True
                                    no_ret_islr = True
                                    no_ret_im = True
                                    
                                    if abs(inv['amount_total'] - pay_line['amount'])<= 1.0:
                                        print 'entre al if 4'
                                        perc_ret_iva = 0.0
                                        perc_ret_islr = 0.0
                                        perc_ret_im = 0.0
                                        no_ret_iva = False
                                        no_ret_islr = False
                                        no_ret_im = False
                                    elif abs((inv['amount_untaxed']*(1+(perc_iva/100)*(1-75.0/100))) - pay_line['amount'])<= 1.0:
                                        print 'entre al elif 1'
                                        perc_ret_iva = 75.0
                                        perc_ret_islr = 0.0
                                        perc_ret_im = 0.0
                                        no_ret_iva = False
                                        no_ret_islr = False
                                        no_ret_im = False
                                    elif ret_iva_lines.search(cr, user, [('invoice_id', '=', inv_id)]):                                
                                        print 'entre al elif 2'
                                        lines_ret_iva = ret_iva_lines.search(cr, user, [('invoice_id', '=', inv_id)])
                                        for line in lines_ret_iva:
                                            print 'entre al for 2'
                                            perc_ret_iva = ret_iva_lines.browse(cr, user, line, context=None).wh_iva_rate
                                        no_ret_iva = False

                                    if no_ret_islr == True and ret_islr_lines.search(cr, user, [('invoice_id', '=', inv_id)]):
                                        print 'entre al if 5'
                                        lines_ret_islr = ret_islr_lines.search(cr, user, [('invoice_id', '=', inv_id)])
                                        perc_ret_islr = 0
                                        for line in lines_ret_islr:
                                            print 'entre al for 3'
                                            perc_ret_islr += ret_islr_lines.browse(cr, user, line, context=None).retencion_islr
                                        no_ret_islr = False
                                        
                                    if no_ret_im == True and ret_im_lines.search(cr, user, [('invoice_id', '=', inv_id)]):
                                        print 'entre al if 6'
                                        lines_ret_im = ret_im_lines.search(cr, user, [('invoice_id', '=', inv_id)])
                                        perc_ret_im = 0
                                        for line in lines_ret_im:
                                            print 'entre al for 4'
                                            perc_ret_im += ret_im_lines.browse(cr, user, line, context=None).wh_loc_rate
                                        no_ret_im = False
                                    
                                    # Tratando de obtener la perc_ret_iva cuando se tiene el valor de impuesto municipal 
                                    # y considerando que el islr es cero, como en el caso de las empresas que solo cargan un impuesto social
                                    
                                    if no_ret_im == False and no_ret_iva == True:
                                        print 'entre al if 7'
                                        for valor in [0, 75.0, 100.0]:
                                            print 'entre al for 5'
                                            if abs((inv['amount_untaxed']*(1+(perc_iva/100)*(1-valor/100.0)-(perc_ret_im/100.0))) - pay_line['amount'])<= 1.0:
                                                print 'entre al if 8'
                                                perc_ret_iva = valor
                                                no_ret_iva = False
                                    
                                    # Tratando de obtener la perc_ret_iva cuando se tiene el valor de impuesto slr 
                                    # y considerando que el im es cero, como en el caso de las empresas que solo cargan el islr y no el im
                                    
                                    if no_ret_islr == False and no_ret_iva == True:
                                        print 'entre al if 9'
                                        for valor in [0, 75.0, 100.0]:
                                            print 'entre al for 6'
                                            if abs((inv['amount_untaxed']*(1+(perc_iva/100)*(1-valor/100.0)-(perc_ret_islr/100.0))) - pay_line['amount'])<= 1.0:
                                                perc_ret_iva = valor
                                                no_ret_iva = False
                                    
                                    # Tratando de obtener la perc_ret_iva cuando se tienen tanto el islr como el im
                                    
                                    if no_ret_islr == False and no_ret_im == False and no_ret_iva == True:
                                        print 'entre al if 10'
                                        for valor in [0, 75.0, 100.0]:
                                            print 'entre al for 7'
                                            if abs((inv['amount_untaxed']*(1+(perc_iva/100)*(1-valor/100.0)-(perc_ret_im/100.0)-(perc_ret_islr/100.0))) - pay_line['amount'])<= 1.0:
                                                print 'entre al if 11'
                                                perc_ret_iva = valor
                                                no_ret_iva = False
                                    
                                    # Tratando de obtener el islr cuando se tienen tanto el perc_ret_iva como el im
                                    if no_ret_islr == True and no_ret_im == False and no_ret_iva == False:
                                        for valor in [0, 2.0, 3.0, 5.0]:
                                            if abs((inv['amount_untaxed']*(1+(perc_iva/100)*(1-perc_ret_iva/100.0)-(perc_ret_im/100.0)-(valor/100.0))) - pay_line['amount'])<= 1.0:
                                                perc_ret_islr = valor
                                                no_ret_islr = False
                                                                    
                                    # Obtener el vendedor del partner
                                    saleman = partner_ids.read(cr,user,inv['partner_id'][0],['user_id'],context=None)['user_id']
                                    
                                    # si ha sido posible calcular u obtener todas las retenciones por los medios convencionales
                                    # entonces se puede proceder con el calculo de retencion de las lineas, de lo contrario se 
                                    # genera una bitacora para que se obtengan las retenciones faltantes para proceder nuevament
                                    # con la preparacion de las comisiones.
                                    if no_ret_islr == False and no_ret_im == False and no_ret_iva == False:
                                        
                                        # Revision de cada linea de factura (productos)
                                        for l_id in inv['invoice_line']:
                                            
                                            #Obtener valores de las lineas
                                            inv_lin = invoice_lines.read(cr,user,l_id,['name', 'price_unit', 'price_subtotal', 'quantity', 'product_id'],context=None)
                                            
                                            #~ print 'Producto: ', inv_lin['name'], '\n'
                                            
                                            # Verificar si tiene producto asociado
                                            if inv_lin['product_id']:
                                                
                                                # Si esta aqui es porque hay un producto asociado
                                                prod_id = inv_lin['product_id'][0]
                                                print 'prod_id',prod_id
                                                # se obtienen las listas de precio, vienen ordenadas por defecto, de acuerdo al objeto
                                                # product.historic de mayor a menor fecha
                                                price_ids = prod_prices.search(cr, user, [('product_id', '=', prod_id)])
                                                print 'price_ids',price_ids
                                                # Buscar Precio Historico de Venta de este 
                                                # producto @ la fecha de facturacion
                                                no_price = True
                                                
                                                for price_id in price_ids:
                                                    print "inv['date_invoice']",inv['date_invoice'] 
                                                    print "prod_prices.browse(cr, user, price_id, context=None).name",prod_prices.browse(cr, user, price_id, context=None).name
                                                    if inv['date_invoice'] >= prod_prices.browse(cr, user, price_id, context=None).name:
                                                        print 'entreeeeeee en el if '
                                                        list_price = prod_prices.browse(cr, user, price_id, context=None).price
                                                        list_date = prod_prices.browse(cr, user, price_id, context=None).name
                                                        no_price = False
                                                        #~ print '[date_invoice : list_price : list_date]: [', inv['date_invoice'],' : ', list_price,' : ', list_date,'] \n' 
                                                        break
                                                print 'no_price',no_price
                                                if no_price == False:
                                                    print 'entreeeeeeeee aquiiiiiiiii'
                                                    # Determinar cuanto fue el descuento en este producto en aquel momento de la venta
                                                    #~ if (inv_lin['price_subtotal']/inv_lin['quantity'])< inv_lin['price_unit']:
                                                    if abs((inv_lin['price_subtotal']/inv_lin['quantity']) - inv_lin['price_unit']) > 0.05:
                                                        # con esto se asegura que no se esta pasando por alto el descuento en linea
                                                        price_unit = round((inv_lin['price_subtotal']/inv_lin['quantity']),2)
                                                    else:
                                                        price_unit = inv_lin['price_unit']
                                                    if list_price:
                                                        dcto= round((list_price - price_unit)*100/list_price,1)
                                                    rate_item= 10.0/100
                                                    
                                                                                                    
                                                    # Determinar dias entre la emision de la factura del producto y el pago del mismo
                                                    pay_date = mx.DateTime.strptime(pay['date'], '%Y-%m-%d')
                                                    inv_date = mx.DateTime.strptime(inv['date_invoice'], '%Y-%m-%d')
                                                    emission_days = (pay_date - inv_date).day

                                                    # Teniendose dias y descuento por producto se procede a buscar en el baremo
                                                    # el correspondiente valor de comision para el producto en cuestion.
                                                    # se entra con el numero de dias
                                                    
                                                    # Esta busqueda devuelve los dias ordenadados de menor a mayor dia, de acuerdo
                                                    # con lo estipulado que se ordenaria en el modulo baremo
                                                    bar_day_ids = commission.bar_id.bar_ids 
                                                    
                                                    no_days = True
                                                    no_dcto = True
                                                    for day_id in bar_day_ids:
                                                        # Se busca que el baremo tenga un rango que cubra a emision_days
                                                        if emission_days <= day_id.number:
                                                            bar_day = day_id.number
                                                            no_days = False
                                                            no_dcto = True
                                                            for dcto_id in day_id.disc_ids:
                                                                # Se busca que el baremo tenga un rango para el valor de descuento en producto
                                                                if (dcto - dcto_id.porc_disc) <= 0.01:
                                                                    bar_dcto_disc = dcto_id.porc_disc
                                                                    if bar_dcto_disc == 0.0:
                                                                        # cuando el descuento en baremo es cero (0) no aparece reflejado,
                                                                        # forzamos a que sea un cero (0) string.
                                                                        bar_dcto_disc = 0.0
                                                                    bar_dcto_comm = dcto_id.porc_com
                                                                    no_dcto = False
                                                                    break
                                                            break
                                                    
                                                    if no_days == False and no_dcto == True:
                                                            bar_dcto_comm = 0.0
                                                            bar_dcto_disc  = 0.0
                                                    
                                                    # Si emission_days no es cubierto por ningun rango del baremo
                                                    # diremos entonces que la comision es cero (0) %
                                                    elif no_days == True and no_dcto == True:
                                                        # Diremos que los dias de baremo es menos uno (-1) cuando los dias de emision
                                                        # no esten dentro del rango del baremo
                                                        bar_day= 'N/A'
                                                        bar_dcto_disc  = 0.0
                                                        bar_dcto_comm = 0.0

                                                    #############################################
                                                    # CALCULO DE COMISION POR LINEA DE PRODUCTO #
                                                    #############################################
                                                    
                                                    ## TODO: ESTE VALOR DEBE DESAPARECER DE AQUI
                                                    #  este valor se debe sustituir por un valor que viene de la factura
                                                    #  son solo demostrativos y no deberian quedar aqui luego de enviar
                                                    #  este modulo a produccion.
                                                    #
                                                    ## 
                                                    
                                                    PenBxLinea = pay_line['amount']*(inv_lin['price_subtotal']/inv['amount_untaxed'])
                                                    Fact_Sup = 1 - perc_ret_islr/100 - perc_ret_im/100
                                                    Fact_Inf = 1 + (perc_iva/100) * (1 - perc_ret_iva/100) - perc_ret_islr/100 - perc_ret_im/100
                                                    
                                                    comm_line =  PenBxLinea * Fact_Sup * (bar_dcto_comm / 100) / Fact_Inf
                                                    # Generar las lineas de comision por cada producto
                                                    
                                                    print 'holaaaaaaaaaaaaaa'
                                                    
                                                    aux= {
                                                        'commission_id': commission.id,
                                                        'voucher_id': vid,
                                                        'name':  pay['name'] and pay['name'] or '/', 
                                                        'pay_date': pay['date'], 
                                                        'pay_off': pay['amount'], 
                                                        'concept': pid  ,
                                                        'invoice_id': pay_line['invoice_id'][0] ,
                                                        'invoice_num':  inv['number'],
                                                        'partner_id': inv['partner_id'][0] ,
                                                        'saleman_name': saleman[1] ,
                                                        'saleman_id': saleman[0] ,
                                                        'pay_inv': pay_line['amount'], 
                                                        'inv_date': inv['date_invoice'],
                                                        'days': emission_days,
                                                        'inv_subtotal': inv['amount_untaxed'],
                                                        'item': inv_lin['name'],
                                                        'price_unit':  price_unit, 
                                                        'price_subtotal':  inv_lin['price_subtotal'], 
                                                        'price_list':  list_price, 
                                                        'price_date': list_date ,
                                                        'perc_ret_islr' : perc_ret_islr,
                                                        'perc_ret_im' : perc_ret_im,
                                                        'perc_ret_iva' : perc_ret_iva,
                                                        'perc_iva' : perc_iva,
                                                        'rate_item': rate_item, 
                                                        'rate_number': bar_dcto_disc,
                                                        'timespan': bar_day,
                                                        'baremo_comm': bar_dcto_comm,
                                                        'commission': comm_line,
                                                    }
                                                    
                                                    
                                                    
                                                    
                                                    comm_line_ids.create(cr, user,{
                                                        'commission_id': commission.id,
                                                        'voucher_id': vid,
                                                        'name':  pay['name'] and pay['name'] or '/', 
                                                        'pay_date': pay['date'], 
                                                        'pay_off': pay['amount'], 
                                                        'concept': pid  ,
                                                        'invoice_id': pay_line['invoice_id'][0] ,
                                                        'invoice_num':  inv['number'],
                                                        'partner_id': inv['partner_id'][0] ,
                                                        'saleman_name': saleman[1] ,
                                                        'saleman_id': saleman[0] ,
                                                        'pay_inv': pay_line['amount'], 
                                                        'inv_date': inv['date_invoice'],
                                                        'days': emission_days,
                                                        'inv_subtotal': inv['amount_untaxed'],
                                                        'item': inv_lin['name'],
                                                        'price_unit':  price_unit, 
                                                        'price_subtotal':  inv_lin['price_subtotal'], 
                                                        'price_list':  list_price, 
                                                        'price_date': list_date ,
                                                        'perc_ret_islr' : perc_ret_islr,
                                                        'perc_ret_im' : perc_ret_im,
                                                        'perc_ret_iva' : perc_ret_iva,
                                                        'perc_iva' : perc_iva,
                                                        'rate_item': rate_item, 
                                                        'rate_number': bar_dcto_disc,
                                                        'timespan': bar_day,
                                                        'baremo_comm': bar_dcto_comm,
                                                        'commission': comm_line,
                                                    },context=None)

                                                else:
                                                    # Se genera un lista de tuplas con las lineas, productos y sus correspondientes fechas
                                                    # en las cuales no aparece precio de lista, luego al final se escriben los
                                                    # valores en la correspondiente bitacora para su inspeccion.
                                                    #~ print 'No hubo precio de lista para la fecha estipulada, hay que generar el precio en este producto \n'
                                                    noprice_ids.create(cr, user,{
                                                        'commission_id': commission.id,
                                                        'product_id': prod_id,
                                                        'date': inv['date_invoice'],
                                                        'invoice_num': inv['number'],
                                                    },context=None)  
                                            else:
                                                # cuando una linea no tiene product_id asociado se escribe en una tabla para alertar al operador
                                                # sobre esta parte no llego a un acuerdo de si se podria permitir al operador cambiar las lineas
                                                # de la factura puesto que es un asunto muy delicado.
                                                pass
                                                sale_noids.create(cr, user,{
                                                    'commission_id' :   commission.id,
                                                    'inv_line_id'   :   l_id,
                                                },context=None)  
                                    else:
                                        # generar campo y vista donde se han de cargar las facturas que tienen problemas
                                        # se debe grabar los tres campos de las retenciones y el numero de la factura para 
                                        # tener detalles concisos y porcion de voucher de pago de la factura en cuestion
                                        comm_retention_ids.create(cr, user,{
                                            'commission_id' :   commission.id,
                                            'invoice_id': pay_line['invoice_id'][0],
                                            'voucher_id':vid,
                                            'date': pay['date'],
                                            'ret_iva': no_ret_iva,
                                            'ret_islr':  no_ret_islr,
                                            'ret_im': no_ret_im,
                                        },context=None)
                                elif (pay_line['invoice_id']==False and pay_line['paid_comm']==False):
                                    # Si esta aqui dentro es porque esta linea (transaccion) no tiene factura valida, se escribe
                                    # entonces una linea en una vista donde se muestran las transacciones que no tienen factura 
                                    # asociada para su correccion si aplica. tampoco se ha pagado la comision del mismo
                                    # solo se incluiran pagos que sean de cuentas cobrables, puesto que las de otra naturaleza,
                                    # no tienen sentido mostrarlas aqui.
                                    if accounts.read(cr, user, pay_line['account_id'][0],['type'], context=None)['type']== 'receivable':
                                        uninvoiced_pays.create(cr, user,{
                                            'commission_id' :   commission.id,
                                            'payment_id'    :   pid,
                                        },context=None)
                            else:
                                #~ No se hace nada por que el vendedor del pago que se esta consultando no se incorporo
                                #~ a la lista de asesores a los que se debe calcular la comision
                                pass
        # habiendo recorrido todos los vouchers, mostrado todos los elementos que necesitan correccion
        # se procede a agrupar las comisiones por vendedor para mayor facilidad de uso
        
        # comm_line_ids.unlink(cr, user, [line_ids.id for line_ids in commission.comm_line_ids])
        
        # recargando las lineas que se han creado
        commissions = self.browse(cr, user, ids, context=None)
        saleman_ids = self.pool.get ('commission.saleman')
        comm_voucher_ids = self.pool.get ('commission.voucher')
        comm_retention_ids = self.pool.get ('commission.retention')
        #~ print 'antes de calcular totales\n'
        
        for commission in commissions:
            
            print 'for commission',commission.comm_line_ids
            # recoge todos los vendedores y suma el total de sus comisiones
            sale_comm = {}
            # ordena en un arbol todas las lineas de comisiones de producto
            criba = {}
            for comm_line in commission.comm_line_ids:
                print 'entre al for'
                vendor_id = comm_line.saleman_id.id
                voucher_id = comm_line.voucher_id.id
                invoice_id = comm_line.invoice_id.id
                comm_line_id = comm_line.id
                
                if not vendor_id in sale_comm.keys():
                    sale_comm[vendor_id]=[comm_line.saleman_name, 0.0]
                sale_comm[vendor_id][1] += comm_line.commission
                
                if not vendor_id in criba.keys():
                     criba[vendor_id] = {}
                     
                if not voucher_id in criba[vendor_id].keys():
                     criba[vendor_id][voucher_id] = [comm_line.pay_date,{}]
                     
                if not invoice_id in criba[vendor_id][voucher_id][1].keys():
                     criba[vendor_id][voucher_id][1][invoice_id] = {}
                     
                if len(criba[vendor_id][voucher_id][1][invoice_id])==0:
                     criba[vendor_id][voucher_id][1][invoice_id]=[[], comm_line.pay_inv, comm_line.perc_ret_iva, comm_line.perc_ret_islr, comm_line.perc_ret_im]
                
                criba[vendor_id][voucher_id][1][invoice_id][0].append(comm_line_id)

            ## escribir el total para cada vendedor encontrado
            total_comm = 0
            for vendor_key in criba.keys():
                print 'fooooooooor'
                vendor_id = saleman_ids.create(cr, user,{
                    'commission_id': commission.id,
                    'saleman_id': vendor_key,
                    'saleman_name':  sale_comm[vendor_key][0],
                    'comm_total': sale_comm[vendor_key][1],
                }, context=None)

                total_comm += sale_comm[vendor_key][1]

                for voucher_key in criba[vendor_key].keys():
                    voucher_id = comm_voucher_ids.create(cr, user,{
                        'commission_id': commission.id,
                        'comm_sale_id': vendor_id,
                        'voucher_id':  voucher_key,
                        'date':  criba[vendor_key][voucher_key][0],
                    }, context=None)
                        
                    for inv_key in criba[vendor_key][voucher_key][1].keys():
                        invoice_id = comm_invoice_ids.create(cr, user,{
                            'commission_id': commission.id,
                            'comm_voucher_id': voucher_id,
                            'invoice_id':  inv_key,
                            'pay_inv':  criba[vendor_key][voucher_key][1][inv_key][1],
                            'ret_iva':  criba[vendor_key][voucher_key][1][inv_key][2],
                            'ret_islr':  criba[vendor_key][voucher_key][1][inv_key][3],
                            'ret_im':  criba[vendor_key][voucher_key][1][inv_key][4],
                        }, context=None)
                        
                        for id in criba[vendor_key][voucher_key][1][inv_key][0]:
                            comm_line_ids.write(cr, user, id, {
                                'comm_invoice_id': invoice_id,
                            }, context=None)
            
            self.write(cr, user, ids, {
                'total_comm': total_comm,
            })
        result = None
        return result

    def pre_process(self, cr, user, ids, context={}):
        commissions = self.browse(cr, user, ids, context=None)
        for commission in commissions:
            self.prepare(cr, user, ids, context=None)
            
            if commission.comm_line_ids:
                self.write(cr, user, ids, {
                        'state': 'decide',
                    })
            else:
                raise osv.except_osv(_('Atencion !'), _('No Existen Lineas de Comision x Producto que procesar !!!'))
            
            if not commission.noprice_ids:
                self.write(cr, user, ids, {
                        'state': 'decide',
                    })
            else:
                raise osv.except_osv(_('Atencion !'), _('Debe primero solucionar el asunto de los Productos sin Listas de Precio \npara las fechas especificadas antes de continuar'))
            
    
    def delete(self, cr, user, ids, context={}):
        commissions = self.browse(cr, user, ids, context=None)
        
        for commission in commissions:
            self.unlink(cr, user, ids, context=None)
            self.write(cr, user, ids, {
                        'state': 'draft',
                        'total_comm':None,
                    })
    
    def unlink(self, cr, user, ids, context={}):
        
        uninvoiced_pays = self.pool.get ('commission.uninvoiced')
        sale_noids = self.pool.get ('commission.sale.noid')
        noprice_ids = self.pool.get ('commission.noprice')
        comm_line_ids = self.pool.get ('commission.lines')
        saleman_ids = self.pool.get ('commission.saleman')
        #~ users_ids = self.pool.get ('commission.users')
        comm_voucher_ids = self.pool.get ('commission.voucher')
        comm_invoice_ids = self.pool.get ('commission.invoice')
        comm_retention_ids = self.pool.get ('commission.retention')
                
        commissions = self.browse(cr, user, ids, context=None)
        
        for commission in commissions:
            ###
            # Desvincular todos los elementos que esten conectados a este calculo de comisiones
            # * Desvinculando los pagos sin facturas
            uninvoiced_pays.unlink(cr, user, [line.id for line in commission.uninvoiced_ids])
            # * Desvinculando los articulos sin id
            sale_noids.unlink(cr, user, [line.id for line in commission.sale_noids])
            # * Desvinculando los productos sin fecha
            noprice_ids.unlink(cr, user, [line.id for line in commission.noprice_ids])
            # * Desvinculando las lineas de comisiones
            comm_line_ids.unlink(cr, user, [line.id for line in commission.comm_line_ids])
            # * Desvinculando los totales por vendedor
            saleman_ids.unlink(cr, user, [line.id for line in commission.saleman_ids])
            # * Desvinculando los vendedores
            #~ users_ids.unlink(cr, user, [line.id for line in commission.users_ids])
            # * Desvinculando los vouchers afectados
            comm_voucher_ids.unlink(cr, user, [line.id for line in commission.comm_voucher_ids])
            # * Desvinculando los vouchers afectados
            comm_invoice_ids.unlink(cr, user, [line.id for line in commission.comm_invoice_ids])
            # * Desvinculando las facturas con problemas de retenciones
            comm_retention_ids.unlink(cr, user, [line.id for line in commission.comm_retention_ids])
            ###
            
    def decide(self, cr, user, ids, context={}):
        commissions = self.browse(cr, user, ids, context=None)
        avl = self.pool.get('account.voucher.line')
        # escribir en el avl el estado buleano de paid_comm a True para indicar que ya esta comision se esta pagando
        for commission in commissions:
            avl.write(cr, user, [line.concept.id for line in commission.comm_line_ids],{
                'paid_comm': True,
            })
            
        self.write(cr, user, ids, {
            'state': 'done',
        })
    
    def going_back(self, cr, user, ids, context={}):
        self.write(cr, user, ids, {
                'state': 'open',
            })
            
commission_payment()

class commission_uninvoiced(osv.osv):
    """
    Commission Payment Uninvoiced : commission_uninvoiced
    """

    _name = 'commission.uninvoiced'
    
    _columns = {
        'name':fields.char('Comentario', size=256),
        'commission_id':fields.many2one('commission.payment', 'Comision'),
        'payment_id':fields.many2one('account.voucher.line', 'Descripcion de Transaccion'),
    }
    _defaults = {
        'name': lambda *a: None,
    }
commission_uninvoiced()

class commission_sale_noid(osv.osv):
    """
    Commission Payment : commission_sale_noid
    """
    
    _name = 'commission.sale.noid'
    
    _columns = {
        'name':fields.char('Comentario', size=256),
        'commission_id':fields.many2one('commission.payment', 'Comision'),
        'inv_line_id':fields.many2one('account.invoice.line', 'Descripcion de Articulo'),
    }
    _defaults = {
        'name': lambda *a: None,
    }
commission_sale_noid()

class commission_noprice(osv.osv):
    """
    Commission Payment : commission_sale_noid
    """
    
    _name = 'commission.noprice'
    _order = 'product_id'
    
    _columns = {
        'name':fields.char('Comentario', size=256),
        'commission_id':fields.many2one('commission.payment', 'Comision'),
        'product_id':fields.many2one('product.product', 'Producto'),
        'date':fields.date('Fecha'),
        'invoice_num':fields.integer('Numero de Factura'),
        
    }
    _defaults = {
        'name': lambda *a: None,
    }
commission_noprice()

class commission_lines(osv.osv):
    """
    Commission Payment : commission_lines
    """
    
    _name = 'commission.lines'
    _order = 'saleman_id'
    
    _columns = {
        'commission_id':fields.many2one('commission.payment', 'Comision', required=True),
        'name':fields.char('Transaccion', size=256, required=True),
        'pay_date':fields.date('Fecha', required=True),
        'pay_off':fields.float('Pago', digits_compute=dp.get_precision('Commission')),
        
        'voucher_id': fields.many2one('account.voucher', 'Voucher'),
        
        'concept': fields.many2one('account.voucher.line', 'Concepto'),
        'invoice_id': fields.many2one('account.invoice', 'Doc.'),
        'invoice_num': fields.char('Doc.', size=256),
        'partner_id': fields.many2one('res.partner', 'Empresa'),
        'saleman_name': fields.char('Vendedor', size=256, required=True),
        'saleman_id': fields.many2one('res.users', 'Vendedor', required=True),
        'pay_inv': fields.float('Abono Fact.', digits_compute=dp.get_precision('Commission')),
        
        'inv_date': fields.date('Fecha Doc.'),
        'days':fields.float('Dias', digits_compute=dp.get_precision('Commission')),
        
        'inv_subtotal': fields.float('SubTot. Doc.', digits_compute=dp.get_precision('Commission')),
        
        'item': fields.char('Item', size=256, required=True),
        'price_unit': fields.float('Prec. Unit.', digits_compute=dp.get_precision('Commission')),
        'price_subtotal': fields.float('SubTot. Item', digits_compute=dp.get_precision('Commission')),
        
        'price_list': fields.float('Precio Lista', digits_compute=dp.get_precision('Commission')),
        'price_date': fields.date('Fecha Lista'),
        
        'perc_ret_islr': fields.float('Ret ISLR (%)', digits_compute=dp.get_precision('Commission')),
        'perc_ret_im': fields.float('Ret IM (%)', digits_compute=dp.get_precision('Commission')),
        'perc_ret_iva': fields.float('Ret IVA (%)', digits_compute=dp.get_precision('Commission')),
        'perc_iva': fields.float('IVA (%)', digits_compute=dp.get_precision('Commission')),
        
        'rate_item':fields.float('Dcto. (%)', digits_compute=dp.get_precision('Commission')),
        
        'rate_number':fields.float('Bar. Rate (%)', digits_compute=dp.get_precision('Commission')),
        'timespan':fields.float('Bar. Dias', digits_compute=dp.get_precision('Commission')),
        'baremo_comm':fields.float('Baremo %Comm.', digits_compute=dp.get_precision('Commission')),
        'commission':fields.float('Comm. / Item', digits_compute=dp.get_precision('Commission')),
    }
    
    _defaults = {
        'name': lambda *a: None,
    }
commission_lines()

class commission_saleman(osv.osv):
    """
    Commission Payment : commission_saleman
    """
    
    _name = 'commission.saleman'
    _order = 'saleman_name'
    
    _columns = {
        'name':fields.char('Comentario', size=256),
        'commission_id':fields.many2one('commission.payment', 'Comision'),
        'saleman_name': fields.char('Vendedor', size=256, required=True),
        'saleman_id': fields.many2one('res.users', 'Vendedor', required=True),
        'comm_total':fields.float('Comision a pagar', digits_compute=dp.get_precision('Commission')),
        'comm_voucher_ids':fields.one2many('commission.voucher', 'comm_sale_id', 'Vouchers afectados en esta comision', required=False),
    }
    _defaults = {
        'name': lambda *a: None,
    }
commission_saleman()


class commission_voucher(osv.osv):
    """
    Commission Payment : commission_voucher
    """
    
    _name = 'commission.voucher'
    _order = 'date'
    
    _columns = {
        'name':fields.char('Comentario', size=256),
        'commission_id':fields.many2one('commission.payment', 'Comision'),
        'comm_sale_id':fields.many2one('commission.saleman', 'Vendedor'),
        'voucher_id':fields.many2one('account.voucher', 'Voucher'),
        'comm_invoice_ids':fields.one2many('commission.invoice', 'comm_voucher_id', 'Facturas afectadas en esta comision', required=False),
        'date': fields.date('Fecha'),
    }
    _defaults = {
        'name': lambda *a: None,
    }
commission_voucher()

class commission_invoice(osv.osv):
    """
    Commission Payment : commission_invoice
    """
    
    _name = 'commission.invoice'
    _order = 'invoice_id'
    
    _columns = {
        'name':fields.char('Comentario', size=256),
        'commission_id':fields.many2one('commission.payment', 'Comision'),
        'comm_voucher_id':fields.many2one('commission.voucher', 'Voucher'),
        'invoice_id':fields.many2one('account.invoice', 'Factura'), 
        'comm_line_ids':fields.one2many('commission.lines', 'comm_invoice_id', 'Comision por productos', required=False),
        'pay_inv': fields.float('Abono Fact.', digits_compute=dp.get_precision('Commission')),
        'ret_iva': fields.float('% Ret. IVA', digits_compute=dp.get_precision('Commission')),
        'ret_islr': fields.float('% Ret. ISLR', digits_compute=dp.get_precision('Commission')),
        'ret_im': fields.float('% Ret. IM', digits_compute=dp.get_precision('Commission')),
    }
    _defaults = {
        'name': lambda *a: None,
    }
commission_invoice()

class commission_lines_2(osv.osv):
    """
    Commission Payment : commission_lines_2
    """
    
    _inherit = 'commission.lines'
    
    _columns = {
        'comm_invoice_id':fields.many2one('commission.invoice', 'Factura Relacional Interna'),
    }
commission_lines_2()


class commission_retention(osv.osv):
    """
    Commission Payment : commission_retention
    """
    
    _name = 'commission.retention'
    _order = 'invoice_id'
    
    _columns = {
        'name':fields.char('Comentario', size=256),
        'commission_id':fields.many2one('commission.payment', 'Comision'),
        'invoice_id':fields.many2one('account.invoice', 'Factura'),
        'voucher_id':fields.many2one('account.voucher', 'Pagado con...'),
        'date': fields.date('Fecha'),
        'ret_iva':fields.boolean('Ret. IVA'),
        'ret_islr':fields.boolean('Ret. ISLR'),
        'ret_im':fields.boolean('Ret. IM'),
    }
    _defaults = {
        'name': lambda *a: None,
    }
commission_retention()

class VoucherLines(osv.osv):
    _inherit = 'account.voucher.line'
    
    _columns = {
        'paid_comm' : fields.boolean('Comision Pagada?'),
        'partner_id':fields.related('voucher_id', 'partner_id', type='many2one', relation='res.partner', string='Partner',store=True),
    }
    _defaults = {
        'paid_comm': lambda *a: False,
    }

VoucherLines()

#~ class commission_users(osv.osv):
    #~ _name='commission.users'
    #~ _columns={
        #~ 'name':fields.char('Nombre', size=8),
        #~ 'commission_id':fields.many2one('commission.payment', 'Comision'),
        #~ 'user_id': fields.many2one('res.users', 'Vendedor', required=True),
    #~ }
#~ commission_users()
