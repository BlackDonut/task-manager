import { createTheme } from '@mui/material/styles';

// ─────────────────────────────────────────────────────────────────────────────
// 業務システムテーマ
//
// 設計方針（ユーザー要件）:
//   - デフォルトフォント 12px / 最大 14px / 最小 10px
//   - オブジェクトを角張った硬い印象（borderRadius 最大 4px）
//   - 文字色・アクセントは落ち着いた非カラフル配色（業務 UI 標準）
//   - 余白は密度重視（情報密度を高める）
// ─────────────────────────────────────────────────────────────────────────────

// プライマリ: 落ち着いた紺色
const PRIMARY_MAIN = '#0D2EA0';

const theme = createTheme({
  palette: {
    primary: {
      main: PRIMARY_MAIN,
      light: '#2D5499',
      dark: '#102549',
      contrastText: '#FFFFFF',
    },
    secondary: {
      main: '#4A5568',
      light: '#718096',
      dark: '#2D3748',
      contrastText: '#FFFFFF',
    },
    error: {
      main: '#B91C1C',
    },
    warning: {
      main: '#B45309',
    },
    success: {
      main: '#166534',
    },
    info: {
      main: '#1E40AF',
    },
    text: {
      primary: '#1A202C',
      secondary: '#4A5568',
      disabled: '#A0AEC0',
    },
    background: {
      default: '#F7F8FA',
      paper: '#FFFFFF',
    },
    divider: '#E2E8F0',
  },
  shape: {
    // 硬い印象: 角丸を最小化
    borderRadius: 3,
  },
  typography: {
    fontFamily: [
      '"Noto Sans JP"',
      '"Roboto"',
      '"Helvetica"',
      '"Arial"',
      'sans-serif',
    ].join(','),
    // ルートフォントサイズ = 12px（業務システム標準密度）
    htmlFontSize: 12,
    fontSize: 12,
    // 見出し: 最大 14px
    h1: { fontSize: '14px', fontWeight: 600, lineHeight: 1.4 },
    h2: { fontSize: '14px', fontWeight: 600, lineHeight: 1.4 },
    h3: { fontSize: '14px', fontWeight: 600, lineHeight: 1.4 },
    h4: { fontSize: '14px', fontWeight: 600, lineHeight: 1.4 },
    h5: { fontSize: '14px', fontWeight: 600, lineHeight: 1.4 },
    h6: { fontSize: '13px', fontWeight: 600, lineHeight: 1.4 },
    // 本文: 12px
    body1: { fontSize: '12px', lineHeight: 1.6 },
    body2: { fontSize: '12px', lineHeight: 1.6 },
    // 補足・小文字: 10px
    caption: { fontSize: '10px', lineHeight: 1.4 },
    overline: { fontSize: '10px', lineHeight: 1.4, letterSpacing: '0.08em' },
    // ボタン・ラベル
    button: { fontSize: '12px', fontWeight: 500, textTransform: 'none' },
    subtitle1: { fontSize: '12px', fontWeight: 500 },
    subtitle2: { fontSize: '11px', fontWeight: 500 },
  },
  components: {
    MuiButton: {
      defaultProps: {
        disableElevation: true,
        size: 'small',
      },
      styleOverrides: {
        root: {
          borderRadius: 3,
          fontSize: '12px',
          padding: '4px 12px',
          lineHeight: 1.5,
        },
        sizeSmall: {
          padding: '3px 10px',
          fontSize: '12px',
        },
        sizeMedium: {
          padding: '5px 14px',
          fontSize: '12px',
        },
      },
    },
    MuiCard: {
      defaultProps: {
        variant: 'outlined',
      },
      styleOverrides: {
        root: {
          borderRadius: 3,
          borderColor: '#E2E8F0',
        },
      },
    },
    MuiPaper: {
      styleOverrides: {
        root: {
          borderRadius: 3,
        },
        outlined: {
          borderColor: '#E2E8F0',
        },
      },
    },
    MuiTableBody: {
      styleOverrides: {
        root: {
          // ゼブラストライプ（奇数行）: 偶数行は白（background.paper）のまま
          '& .MuiTableRow-root:nth-of-type(odd)': {
            backgroundColor: '#F4F7FB',
          },
        },
      },
    },
    MuiTable: {
      defaultProps: {
        size: 'small',
      },
    },
    MuiTableHead: {
      styleOverrides: {
        root: {
          '& .MuiTableCell-head': {
            backgroundColor: '#EEF2F7',
            color: PRIMARY_MAIN,
            fontWeight: 700,
            fontSize: '11px',
            borderBottomColor: '#C9D5E8',
          },
        },
      },
    },
    MuiTableCell: {
      styleOverrides: {
        root: {
          fontSize: '12px',
          padding: '6px 12px',
          borderBottomColor: '#EEF0F4',
        },
        sizeSmall: {
          padding: '4px 8px',
        },
      },
    },
    MuiTableRow: {
      styleOverrides: {
        root: {
          '&.MuiTableRow-hover:hover': {
            // ゼブラストライプを上書きするため !important
            backgroundColor: '#EBF0F9 !important',
          },
          '&.Mui-selected': {
            backgroundColor: '#D7E3F5 !important',
          },
          '&.Mui-selected.MuiTableRow-hover:hover': {
            backgroundColor: '#C4D5EF !important',
          },
        },
      },
    },
    MuiChip: {
      styleOverrides: {
        root: {
          borderRadius: 3,
          height: 22,
          fontSize: '11px',
          fontWeight: 500,
        },
        colorPrimary: {
          backgroundColor: '#E8EDF7',
          color: PRIMARY_MAIN,
          borderColor: '#B8C7E0',
        },
        colorInfo: {
          backgroundColor: '#EBF3FF',
          color: '#1E40AF',
          borderColor: '#BFDBFE',
        },
        colorSuccess: {
          backgroundColor: '#ECFDF5',
          color: '#166534',
          borderColor: '#A7F3D0',
        },
        colorWarning: {
          backgroundColor: '#FFFBEB',
          color: '#92400E',
          borderColor: '#FDE68A',
        },
        colorError: {
          backgroundColor: '#FEF2F2',
          color: '#991B1B',
          borderColor: '#FECACA',
        },
      },
    },
    MuiAppBar: {
      styleOverrides: {
        colorPrimary: {
          backgroundColor: PRIMARY_MAIN,
        },
      },
    },
    MuiTextField: {
      defaultProps: {
        size: 'small',
      },
    },
    MuiOutlinedInput: {
      styleOverrides: {
        root: {
          borderRadius: 3,
          fontSize: '12px',
          '& .MuiOutlinedInput-notchedOutline': {
            borderColor: '#CBD5E0',
          },
          '&:hover .MuiOutlinedInput-notchedOutline': {
            borderColor: '#718096',
          },
        },
        input: {
          padding: '6px 10px',
          fontSize: '12px',
        },
        sizeSmall: {
          padding: '4px 8px',
          fontSize: '12px',
        },
      },
    },
    MuiInputLabel: {
      styleOverrides: {
        root: {
          fontSize: '12px',
        },
        sizeSmall: {
          fontSize: '12px',
        },
      },
    },
    MuiSelect: {
      defaultProps: {
        size: 'small',
      },
      styleOverrides: {
        select: {
          fontSize: '12px',
        },
      },
    },
    MuiMenuItem: {
      styleOverrides: {
        root: {
          fontSize: '12px',
          minHeight: '32px',
          padding: '4px 12px',
        },
      },
    },
    MuiFormHelperText: {
      styleOverrides: {
        root: {
          fontSize: '10px',
          marginTop: '2px',
        },
      },
    },
    MuiDialog: {
      styleOverrides: {
        paper: {
          borderRadius: 4,
        },
      },
    },
    MuiDialogTitle: {
      styleOverrides: {
        root: {
          fontSize: '13px',
          fontWeight: 600,
          padding: '14px 18px 10px',
          borderBottom: '1px solid #E2E8F0',
        },
      },
    },
    MuiDialogContent: {
      styleOverrides: {
        root: {
          padding: '14px 18px',
          fontSize: '12px',
        },
      },
    },
    MuiDialogActions: {
      styleOverrides: {
        root: {
          padding: '10px 18px',
          borderTop: '1px solid #E2E8F0',
          gap: '8px',
        },
      },
    },
    MuiAlert: {
      styleOverrides: {
        root: {
          borderRadius: 3,
          fontSize: '12px',
          padding: '6px 12px',
        },
        icon: {
          fontSize: '16px',
        },
      },
    },
    MuiTooltip: {
      defaultProps: {
        arrow: true,
      },
      styleOverrides: {
        tooltip: {
          fontSize: '11px',
          borderRadius: 2,
        },
      },
    },
    MuiIconButton: {
      styleOverrides: {
        root: {
          borderRadius: 3,
        },
        sizeSmall: {
          padding: '3px',
        },
      },
    },
    MuiListItemButton: {
      styleOverrides: {
        root: {
          borderRadius: 3,
          paddingTop: '5px',
          paddingBottom: '5px',
          fontSize: '12px',
        },
      },
    },
    MuiListItemText: {
      styleOverrides: {
        primary: {
          fontSize: '12px',
        },
        secondary: {
          fontSize: '11px',
        },
      },
    },
    MuiTab: {
      styleOverrides: {
        root: {
          fontSize: '12px',
          minHeight: 36,
          padding: '6px 12px',
          textTransform: 'none',
        },
      },
    },
    MuiTabs: {
      styleOverrides: {
        root: {
          minHeight: 36,
        },
      },
    },
    MuiBreadcrumbs: {
      styleOverrides: {
        root: {
          fontSize: '11px',
        },
      },
    },
    MuiTypography: {
      styleOverrides: {
        root: {
          // フォント指定のないケースのフォールバック
        },
      },
    },
    MuiSkeleton: {
      defaultProps: {
        animation: 'wave',
      },
    },
    MuiTablePagination: {
      styleOverrides: {
        root: {
          fontSize: '11px',
        },
        selectLabel: {
          fontSize: '11px',
        },
        displayedRows: {
          fontSize: '11px',
        },
      },
    },
  },
});

export default theme;
