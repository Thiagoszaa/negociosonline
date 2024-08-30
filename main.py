import streamlit as st
from datetime import datetime, timedelta
import json
import os

# Caminho para o arquivo JSON que armazena os dados dos processos
DATA_FILE = 'process_data.json'

# Função para carregar os dados do arquivo JSON
def load_data():
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, 'r') as file:
            return json.load(file)
    return []

# Função para salvar os dados no arquivo JSON
def save_data(process_data):
    with open(DATA_FILE, 'w') as file:
        json.dump(process_data, file, default=str)

# Função para verificar processos que estão próximos ou passaram da data de recebimento
def check_alerts(process_data, days_before=2):
    alerts = []
    today = datetime.now().date()
    for process in process_data:
        # Verifica data de recebimento do processo
        if datetime.strptime(process['data_recebimento'], '%Y-%m-%d').date() <= today + timedelta(days=days_before):
            alerts.append({
                'numero_processo': process['numero_processo'],
                'contra_quem': process['contra_quem'],
                'data_processo': process['data_processo'],
                'data_recebimento': process['data_recebimento'],
                'total_valor': sum([parcela['valor'] for parcela in process['parcelas']]),  # Valor total a receber
                'pagamento_tipo': 'Parcelado' if len(process['parcelas']) > 1 else 'À Vista',
                'alert_type': 'Processo',
                'expiration_date': datetime.strptime(process['data_recebimento'], '%Y-%m-%d').date() + timedelta(days=2)
            })
        
        # Verifica datas de vencimento das parcelas
        for parcela in process.get('parcelas', []):
            vencimento = datetime.strptime(parcela['vencimento'], '%Y-%m-%d').date()
            if not parcela.get('pago', False) and today + timedelta(days=1) >= vencimento:
                alerts.append({
                    'numero_processo': process['numero_processo'],
                    'contra_quem': process['contra_quem'],
                    'parcela_numero': parcela['numero'],
                    'valor': parcela['valor'],
                    'vencimento': parcela['vencimento'],
                    'alert_type': 'Parcela',
                    'expiration_date': vencimento + timedelta(days=2)
                })
    
    # Remove alertas que expiraram
    alerts = [alert for alert in alerts if alert['expiration_date'] >= today]
    
    return alerts

# Função para confirmar pagamento de uma parcela ou processo
def confirmar_pagamento(process_data, numero_processo, parcela_numero=None):
    for process in process_data:
        if process['numero_processo'] == numero_processo:
            if parcela_numero is None:
                # Se não houver número de parcela, remove o processo completo
                process_data.remove(process)
            else:
                # Marca a parcela como paga
                for parcela in process['parcelas']:
                    if parcela['numero'] == parcela_numero:
                        parcela['pago'] = True
                        break
            break
    save_data(process_data)

# Função principal do aplicativo Streamlit
def main():
    # Configurações de layout
    st.set_page_config(page_title="Gerenciamento de Processos", layout="wide")
    
    st.title('📋 Gerenciamento de Processos')

    # Carrega os dados dos processos
    process_data = load_data()

    # Barra lateral para adicionar novo processo
    with st.sidebar:
        st.header('Adicionar Novo Processo')
        with st.form('add_process'):
            data_processo = st.date_input('📅 Data do Processo', datetime.now())
            numero_processo = st.text_input('🔢 Número do Processo')
            contra_quem = st.text_input('👤 Reclamada')
            data_recebimento = st.date_input('📅 Data de Recebimento')
            num_parcelas = st.number_input('Número de Parcelas', min_value=1, max_value=30, value=1, step=1)
            valor_parcela = st.number_input('Valor da Parcela', min_value=0.0, step=0.01)
            submit = st.form_submit_button('Adicionar Processo')

        if submit:
            parcelas = []
            for i in range(1, num_parcelas + 1):
                vencimento = data_recebimento + timedelta(days=30 * i)
                parcelas.append({
                    'numero': i,
                    'valor': valor_parcela,
                    'vencimento': str(vencimento),
                    'pago': False  # Inicialmente, a parcela não está paga
                })

            novo_processo = {
                'data_processo': str(data_processo),
                'numero_processo': numero_processo,
                'contra_quem': contra_quem,
                'data_recebimento': str(data_recebimento),
                'parcelas': parcelas
            }
            process_data.append(novo_processo)
            save_data(process_data)  # Salva os dados após adicionar um novo processo
            st.success('Processo adicionado com sucesso!')

    # Verifica se há alertas (processos próximos ou passados e parcelas)
    alerts = check_alerts(process_data)

    # Exibição dos processos com alerta
    st.subheader('⚠️ Pagamentos Próximos ou com Data de Recebimento Passada')
    
    if alerts:
        for alert in alerts:
            if alert['alert_type'] == 'Processo':
                st.markdown(f"### **Número do Processo:** `{alert['numero_processo']}`")
                st.markdown(f"**Contra:** `{alert['contra_quem']} - Pagamento: {alert['pagamento_tipo']} - Valor Total: R$ {alert['total_valor']}`")
                st.markdown(f"**Data do Processo:** `{datetime.strptime(alert['data_processo'], '%Y-%m-%d').strftime('%d/%m/%Y')}`")
                st.markdown(f"**Data de Recebimento:** `{datetime.strptime(alert['data_recebimento'], '%Y-%m-%d').strftime('%d/%m/%Y')}`")
                if datetime.strptime(alert['data_recebimento'], '%Y-%m-%d').date() < datetime.now().date():
                    st.error(f"**Status:** Data de recebimento já passou! 📅")
                else:
                    st.warning(f"**Status:** Data de recebimento próxima! 📅")
                if st.button('Confirmar Pagamento', key=f"processo-{alert['numero_processo']}"):
                    confirmar_pagamento(process_data, alert['numero_processo'])
                    st.success('Processo marcado como pago!')
                    st.rerun()
            elif alert['alert_type'] == 'Parcela':
                st.markdown(f"### **Número do Processo:** `{alert['numero_processo']}`")
                st.markdown(f"**Contra:** `{alert['contra_quem']}`")
                st.markdown(f"**Número da Parcela:** `{alert['parcela_numero']}`")
                st.markdown(f"**Valor da Parcela:** `R$ {alert['valor']}`")
                st.markdown(f"**Vencimento:** `{datetime.strptime(alert['vencimento'], '%Y-%m-%d').strftime('%d/%m/%Y')}`")
                if datetime.strptime(alert['vencimento'], '%Y-%m-%d').date() < datetime.now().date():
                    st.error(f"**Status:** Parcela vencida! 📅")
                else:
                    st.warning(f"**Status:** Vencimento da parcela em 1 dia! 📅")
                if st.button('Confirmar Pagamento', key=f"parcela-{alert['numero_processo']}-{alert['parcela_numero']}"):
                    confirmar_pagamento(process_data, alert['numero_processo'], alert['parcela_numero'])
                    st.success('Parcela marcada como paga!')
                    st.rerun()
            st.markdown("---")
    else:
        st.info('Nenhum processo ou parcela próximo(a) ou com data de recebimento/vencimento passada.')

# Executa o aplicativo Streamlit
if __name__ == '__main__':
    main()
