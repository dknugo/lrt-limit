import streamlit as st
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import requests

PARASWAP_API_URL = "https://apiv5.paraswap.io"
ONEINCH_API_URL = "https://limit-orders.1inch.io/v4.0"

CHAINS_LIST = [
                # [1, 'Ethereum'],
                [42161, 'Arbitrum']
            ]

DEF_TAKER = "weETH"
DEF_MAKER = "WETH"

TOKENS_LIST = [
    [1, '0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2', 'WETH'],
    [1, '0xCd5fE23C85820F7B72D0926FC9b05b43E359b7ee', 'weETH'],
    [1, '0xA1290d69c65A6Fe4DF752f95823fae25cB99e5A7', 'rsETH'],
    [1, '0xbf5495Efe5DB9ce00f80364C8B423567e58d2110', 'ezETH'],
    [1, '0xFAe103DC9cf190eD75350761e95403b7b8aFa6c0', 'rswETH'],
    [1, '0xD9A442856C234a39a81a089C06451EBAa4306a72', 'pufETH'],
    [42161, '0x82aF49447D8a07e3bd95BD0d56f35241523fBab1', 'WETH'],
    [42161, '0x35751007a407ca6FEFfE80b3cB397736D2cf4dbe', 'weETH'],
    [42161, '0x4186BFC76E2E237523CBC30FD220FE055156b41F', 'rsETH'],
    [42161, '0x2416092f143378750bb29b79eD961ab195CcEea5', 'ezETH']
]


# @st.cache_data
# def get_tokens(chain_id):
#     url = API_URL + '/tokens/' + str(chain_id)
#     res = requests.get(url)
#     if res.status_code == 200:
#         if 'tokens' in res.json():
#             if len(res.json()['tokens']) > 0:
#                 return pd.DataFrame(res.json()['tokens'])[['address', 'symbol']]
#         st.info(f'Token list empty')
#         return pd.DataFrame()
#     else:
#         st.error(f'Error fetching token list: {res.status_code}, {res.json()["error"]}')
#         return pd.DataFrame()

@st.cache_data(ttl=60)
def get_limit_orders_paraswap(chain_id, maker_asset, taker_asset):
    url = PARASWAP_API_URL + '/ft/orders/' + str(chain_id) + '/orderbook/?makerAsset=' + maker_asset + '&takerAsset=' + taker_asset
    res = requests.get(url)
    if res.status_code == 200:
        if 'orders' in res.json():
            if len(res.json()['orders']) > 0:
                res_df = pd.DataFrame(res.json()['orders'])
                res_df = res_df[res_df.state == 'PENDING']
                res_df['fillable_amount'] = res_df['fillableBalance'].astype(float) / 1e18
                res_df['maker_amount'] = res_df['makerAmount'].astype(float) / 1e18
                res_df['taker_amount'] = res_df['takerAmount'].astype(float) / 1e18
                res_df['rate'] = res_df['taker_amount'] / res_df['maker_amount']
                return res_df
        st.info(f'No orders found')
        return pd.DataFrame()
    else:
        st.error(f'Error fetching orders: {res.status_code}, {res.json()["error"]}')
        return pd.DataFrame()

@st.cache_data(ttl=60)
def get_limit_orders_oneinch(chain_id, maker_asset, taker_asset):
    
    agg_orders_df = pd.DataFrame()
    page_num = 1
    while True:
        url = ONEINCH_API_URL + '/' + str(chain_id) + '/all?page=' + str(page_num)\
                + '&limit=500&statuses=1'\
                + '&makerAsset=' + maker_asset + '&takerAsset=' + taker_asset
        res = requests.get(url)
        if res.status_code == 200:
            if len(res.json()) > 0:
                orders_df = pd.DataFrame([{'create_time': pd.to_datetime(data['createDateTime']),
                                            'fillable_amount': float(data['remainingMakerAmount']) / 1e18,
                                            'maker_amount': float(data['data']['makingAmount']) / 1e18,
                                            'taker_amount': float(data['data']['takingAmount']) / 1e18,
                                            'maker': data['data']['maker'],
                                            'rate': 1 / float(data['makerRate'])
                                            }
                                            for data in res.json()])
                agg_orders_df = pd.concat([agg_orders_df, orders_df], axis = 0).reset_index()
                page_num = page_num + 1
            elif page_num == 1:
                st.info(f'No orders found')
                break
            else:
                break
        else:
            st.error(f'Error fetching orders: {res.status_code}')
            break

    return agg_orders_df

def click_refresh_paraswap():
    get_limit_orders_paraswap.clear()

def click_refresh_oneinch():
    get_limit_orders_oneinch.clear()


with st.sidebar:
    
    chains_df = pd.DataFrame(data = CHAINS_LIST, columns = ['chain_id', 'name'])
    chain_sel = st.selectbox(
        'Select chain:',
        chains_df,
        format_func = lambda x: chains_df[chains_df.chain_id == x]['name'].squeeze())
    if not chain_sel:
        st.error('Please select chain')
        st.stop()
    else:
        # tokens_df = get_tokens(chain_sel)
        tokens_df = pd.DataFrame(data = TOKENS_LIST, columns = ['chain', 'address', 'symbol'])
        tokens_df = tokens_df[tokens_df.chain == chain_sel][['address', 'symbol']]
        maker_asset = st.selectbox(
            'Select maker asset:',
            tokens_df,
            index = int(tokens_df[tokens_df.symbol == DEF_MAKER].index[0]),
            format_func = lambda x: tokens_df[tokens_df.address == x]['symbol'].squeeze()
        )
        taker_asset = st.selectbox(
            'Select taker asset:',
            tokens_df,
            index = int(tokens_df[tokens_df.symbol == DEF_TAKER].index[0]),
            format_func = lambda x: tokens_df[tokens_df.address == x]['symbol'].squeeze()
        )
        
if not maker_asset:
    st.error('Please select maker asset')
elif not taker_asset:
    st.error('Please select taker asset')
else:
    
    st.title('Limit orders')
    
    tab1, tab2 = st.tabs(["1inch", "Paraswap"])
    with tab1:
        orders_oi = get_limit_orders_oneinch(chain_sel, maker_asset, taker_asset)
        if len(orders_oi) > 0:
            st.button('Refresh', key = 'refresh_oi', on_click = click_refresh_oneinch)
            col3, col4 = st.columns(2)
            total_fillable_balance = orders_oi['fillable_amount'].sum()
            with col3:
                st.metric('Total fillable', f"{total_fillable_balance:,.0f}")
            with col4:
                weighted_rate = (orders_oi['fillable_amount'] * orders_oi['rate'] / total_fillable_balance).sum()
                st.metric('Weighted average rate', f"{weighted_rate:,.3f}")
            
            st.dataframe(
                orders_oi[['fillable_amount', 'maker_amount', 'taker_amount', 'rate', 'maker']].sort_values('fillable_amount', ascending = False),
                hide_index = True      
            )

            fig2, ax2 = plt.subplots()
            fig2.set_figheight(2)
            ax2.hist(x = orders_oi['rate'], weights = orders_oi['fillable_amount'], bins=20)
            st.pyplot(fig2)

    with tab2:
        orders_ps = get_limit_orders_paraswap(chain_sel, maker_asset, taker_asset)
        if len(orders_ps) > 0:
            st.button('Refresh', key = 'refresh_ps', on_click = click_refresh_paraswap)
            col1, col2 = st.columns(2)
            total_fillable_balance = orders_ps['fillable_amount'].sum()
            with col1:
                st.metric('Total fillable', f"{total_fillable_balance:,.0f}")
            with col2:
                weighted_rate = (orders_ps['fillable_amount'] * orders_ps['rate'] / total_fillable_balance).sum()
                st.metric('Weighted average rate', f"{weighted_rate:,.3f}")
            
            st.dataframe(
                orders_ps[['fillable_amount', 'maker_amount', 'taker_amount', 'rate', 'maker']].sort_values('fillable_amount', ascending = False),
                hide_index = True      
            )

            fig1, ax1 = plt.subplots()
            fig1.set_figheight(2)
            ax1.hist(x = orders_ps['rate'], weights = orders_ps['fillable_amount'], bins=20)
            st.pyplot(fig1)