import { MenubarItem, MenubarShortcut } from "@/renderer/components/ui/menubar";
import { useSave } from "@/renderer/hooks/useSave";
import { useSaveAs } from "@/renderer/hooks/useSaveAs";

export const SaveButton = () => {
  const handleSave = useSave();

  return (
    <MenubarItem data-testid="btn-save" onClick={handleSave}>
      {/* TODO: Add logo for windows and linux */}
      Save <MenubarShortcut>⌘S</MenubarShortcut>
    </MenubarItem>
  );
};

export const SaveAsButton = () => {
  const { handleSaveAs, SaveAsDialog } = useSaveAs();

  return (
    <>
      <MenubarItem data-testid="btn-saveas" onClick={handleSaveAs}>
        Save As <MenubarShortcut>⇧⌘S</MenubarShortcut>
      </MenubarItem>
      <SaveAsDialog />
    </>
  );
};
