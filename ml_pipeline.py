import pandas as pd
import joblib

def process_uploaded_files(uploaded_files):
    """
    الدالة دي بتستقبل الملفات الأربعة المرفوعة، 
    وبتطبق كل موديل على الشيت بتاعه مع فلترة الأعمدة الزيادة وحل مشكلة المسافات.
    """
    # 1. تحميل الموديلات 
    kmeans_model = joblib.load('kmeans_model.pkl')
    xgb_model = joblib.load('xgb_model.pkl')
    rf_model = joblib.load('npd_model.pkl') 

    data_dict = {}

    # 2. قراءة كل ملف وتطبيق الموديل المناسب
    for file in uploaded_files:
        df = pd.read_csv(file)
        
        # 🔴 تنظيف أسماء الأعمدة من أي مسافات مخفية (بتعمل مشاكل كتير في الإكسيل) 🔴
        df.columns = df.columns.str.strip()
        
        file_name = file.name.lower()

        # ==================================
        # 1. موديل التقسيم (Segmentation)
        # ==================================
        if 'segment' in file_name:
            # 🔴 الحل السحري: خلي الموديل يختار الأعمدة اللي اتدرب عليها بالظبط 🔴
            if hasattr(kmeans_model, 'feature_names_in_'):
                X_seg = df[kmeans_model.feature_names_in_]
            else:
                # لو الموديل إصدار قديم ومش متسجل فيه أسماء، هنحاول نلاقي الأعمدة الصح
                if 'R' in df.columns and 'F' in df.columns and 'M' in df.columns:
                    X_seg = df[['R', 'F', 'M']]
                else:
                    X_seg = df[['Recency', 'Frequency', 'Monetary']]
                    
            df['prediction'] = kmeans_model.predict(X_seg)
            segment_map = {0: 'Champions', 1: 'Loyal', 2: 'At Risk', 3: 'Lost'}
            df['Segment'] = df['prediction'].map(segment_map)
            data_dict['segmentation'] = df

        # ==================================
        # 2. موديل الهروب (Churn Prediction)
        # ==================================
        elif 'churn' in file_name:
            if hasattr(xgb_model, 'feature_names_in_'):
                X_churn = df[xgb_model.feature_names_in_]
            else:
                cols_to_drop = [c for c in df.columns if 'unnamed' in c.lower() or 'prediction' in c.lower() or c in ['Customer ID', 'is_churn', 'churn_prediction_rate']]
                X_churn = df.drop(columns=cols_to_drop, errors='ignore')
            
            df['churn_prediction_rate'] = xgb_model.predict_proba(X_churn)[:, 1] * 100 
            df['prediction'] = df['churn_prediction_rate'] 
            df['is_churn'] = (df['churn_prediction_rate'] > 75).astype(int) 
            data_dict['churn'] = df

        # ==================================
        # 3. موديل موعد الشراء القادم (Next Purchase)
        # ==================================
        elif 'next' in file_name or 'purchase' in file_name:
            if hasattr(rf_model, 'feature_names_in_'):
                X_next = df[rf_model.feature_names_in_]
            else:
                cols_to_drop = [c for c in df.columns if 'unnamed' in c.lower() or 'prediction' in c.lower() or c in ['Customer ID', 'labels']]
                X_next = df.drop(columns=cols_to_drop, errors='ignore')
            
            df['predictions'] = rf_model.predict(X_next)
            df['prediction'] = df['predictions'] 
            data_dict['next_purchase'] = df

        # ==================================
        # 4. حساب القيمة للعميل (CLV)
        # ==================================
        elif 'clv' in file_name:
            def classify_clv(x):
                if x <= 281: return 'Bronze'
                elif x <= 796: return 'Silver'
                elif x <= 2668: return 'Gold'
                else: return 'Platinum'
            
            df['CLV_segment'] = df['CLV'].apply(classify_clv)
            df['prediction'] = df['CLV_segment']
            data_dict['clv'] = df

    # ==================================
    # 5. تجميع الداتا لصفحة الـ Search ID أوتوماتيك
    # ==================================
    if all(k in data_dict for k in ['segmentation', 'churn', 'clv', 'next_purchase']):
        df1 = data_dict['segmentation'][['Customer ID', 'Segment']].rename(columns={'Segment': 'Segmentation'})
        df2 = data_dict['churn'][['Customer ID', 'is_churn']].rename(columns={'is_churn': 'Churn'})
        df3 = data_dict['clv'][['Customer ID', 'CLV_segment']].rename(columns={'CLV_segment': 'CLV'})
        df4 = data_dict['next_purchase'][['Customer ID', 'predictions']].rename(columns={'predictions': 'Next_purchase_predictions'})

        search_df = df1.merge(df2, on='Customer ID', how='outer')\
                       .merge(df3, on='Customer ID', how='outer')\
                       .merge(df4, on='Customer ID', how='outer')
        
        data_dict['search_id'] = search_df

    return data_dict