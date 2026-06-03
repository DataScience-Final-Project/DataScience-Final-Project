export const dashboardTheme = {

  token: {

    colorPrimary: '#4318FF',

    colorSuccess: '#10B981',

    borderRadius: 16,

    borderRadiusLG: 20,

    fontFamily: `'Poppins', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif`,

    colorBgLayout: '#F4F7FE',

    colorBgContainer: '#FFFFFF',

    colorText: '#1E293B',

    colorTextSecondary: '#64748B',

    colorTextTertiary: '#A3AED0',

    colorBorderSecondary: 'rgba(148, 163, 184, 0.35)',

    controlHeightLG: 44,

    paddingLG: 24,

    paddingMD: 20,

    paddingSM: 16,

    boxShadow:

      '0 10px 30px rgba(15, 23, 42, 0.06)',

    boxShadowSecondary:

      '0 4px 14px rgba(67, 24, 255, 0.08)',

    wireframe: false,

  },

  components: {

    Card: {

      borderRadiusLG: 20,

      headerBg: 'transparent',

      boxShadowTertiary: '0 10px 30px rgba(15, 23, 42, 0.06)',

    },

    Button: {

      primaryShadow: '0 8px 22px rgba(67, 24, 255, 0.32)',

      defaultShadow: '0 4px 14px rgba(15, 23, 42, 0.06)',

      borderRadius: 12,

      controlHeightLG: 46,

    },

    Slider: {

      railBg: '#EDF2FF',

      railHoverBg: '#E2E8FF',

      trackBg: '#C8BFFF',

      trackHoverBg: '#A89AFF',

      handleColor: '#4318FF',

      handleActiveColor: '#3512CC',

      dotActiveBorderColor: '#4318FF',

      handleActiveOutlineColor: 'rgba(67, 24, 255, 0.22)',

    },

    Segmented: {

      trackBg: '#EEF2FF',

      itemSelectedBg: '#FFFFFF',

      itemSelectedColor: '#4318FF',

      itemHoverBg: 'rgba(67, 24, 255, 0.08)',

      itemHoverColor: '#1E293B',

      itemActiveBg: 'rgba(67, 24, 255, 0.12)',

    },

    Input: {

      activeBorderColor: '#4318FF',

      hoverBorderColor: '#B8AEFF',

      borderRadiusLG: 14,

      colorBgContainer: '#FFFFFF',

    },

    Form: {

      labelColor: '#64748B',

      verticalLabelPadding: '0 0 8px',

    },

    Divider: {

      marginLG: 24,

      colorSplit: 'rgba(148, 163, 184, 0.35)',

    },

  },

} as const
