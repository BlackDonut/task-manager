/**
 * Axios HTTP クライアント設定。
 * 全 API 呼び出しの共通設定（baseURL・Cookies 認証・ Accept-Language ヘッダ）を提供する。
 * 仕様: docs/03_detail-design/01_common/api-common.md
 * 業務制約: ロケールと認証イベントは未実装 UI に依存させず最小構成でも動作させる
 */
import axios from 'axios';

const AUTH_CHANNEL_NAME = 'task-manager-auth';
const DEFAULT_LOCALE = 'ja';

/**
 * 永続化済みロケールを返す。
 */
function getStoredLocale(): string {
  if (typeof window === 'undefined') {
    return DEFAULT_LOCALE;
  }

  return window.localStorage.getItem('locale') ?? DEFAULT_LOCALE;
}

const apiClient = axios.create({
  baseURL: '/api/v1',
  headers: {
    'Content-Type': 'application/json',
  },
  withCredentials: true,
});

// --- Accept-Language: サーバー側 i18n（業務メッセージ）に現在ロケールを伝える ---
// ADR-0004 §D3 選択肢 B（ハイブリッド）の要請。
apiClient.interceptors.request.use((config) => {
  const locale = getStoredLocale();
  config.headers = config.headers ?? {};
  config.headers['Accept-Language'] = locale;
  return config;
});

apiClient.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      // セッション失効を他タブに通知してから自タブはログインページへリダイレクト。
      // BroadcastChannel は同一オリジン内の他タブにのみ届き、自タブへは届かない仕様。
      try {
        const ch = new BroadcastChannel(AUTH_CHANNEL_NAME);
        ch.postMessage({ type: 'logout' });
        ch.close();
      } catch {
        // BroadcastChannel 非対応環境ではスキップ。
      }
      window.location.href = '/login';
    }
    return Promise.reject(error);
  }
);

export default apiClient;
