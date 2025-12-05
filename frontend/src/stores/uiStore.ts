import { create } from 'zustand';
import { persist } from 'zustand/middleware';

interface UIState {
  // Sidebar
  sidebarCollapsed: boolean;
  toggleSidebar: () => void;
  setSidebarCollapsed: (collapsed: boolean) => void;

  // Theme
  darkMode: boolean;
  toggleDarkMode: () => void;

  // Message list filters (persisted for convenience)
  messageFilters: {
    source?: string;
    sentiment?: string;
    category_id?: string;
    dateRange?: [string, string];
    search?: string;
    page_size?: number;
  };
  setMessageFilters: (filters: UIState['messageFilters']) => void;
  clearMessageFilters: () => void;

  // Selected items for bulk actions
  selectedMessageIds: string[];
  setSelectedMessageIds: (ids: string[]) => void;
  clearSelectedMessages: () => void;
}

export const useUIStore = create<UIState>()(
  persist(
    (set) => ({
      // Sidebar
      sidebarCollapsed: false,
      toggleSidebar: () =>
        set((state) => ({ sidebarCollapsed: !state.sidebarCollapsed })),
      setSidebarCollapsed: (collapsed) => set({ sidebarCollapsed: collapsed }),

      // Theme
      darkMode: false,
      toggleDarkMode: () => set((state) => ({ darkMode: !state.darkMode })),

      // Message filters
      messageFilters: {},
      setMessageFilters: (filters) => set({ messageFilters: filters }),
      clearMessageFilters: () => set({ messageFilters: {} }),

      // Selected messages
      selectedMessageIds: [],
      setSelectedMessageIds: (ids) => set({ selectedMessageIds: ids }),
      clearSelectedMessages: () => set({ selectedMessageIds: [] }),
    }),
    {
      name: 'dewey-ui',
      partialize: (state) => ({
        sidebarCollapsed: state.sidebarCollapsed,
        darkMode: state.darkMode,
        messageFilters: state.messageFilters,
      }),
    }
  )
);
