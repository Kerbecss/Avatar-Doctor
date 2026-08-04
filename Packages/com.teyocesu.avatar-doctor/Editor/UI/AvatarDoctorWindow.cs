using Teyocesu.AvatarDoctor.Editor.Core;
using UnityEditor;
using UnityEngine;
using UnityEngine.UIElements;

namespace Teyocesu.AvatarDoctor.Editor.UI
{
    internal sealed class AvatarDoctorWindow : EditorWindow
    {
        private const string MenuPath = "Tools/Avatar Doctor";
        private const int MenuPriority = 2000;
        private const float MinimumWidth = 420f;
        private const float MinimumHeight = 220f;
        private const string StatusText = "Pre-alpha - Window shell";
        private const string UnavailableAnalysisMessage = "Avatar analysis is not available in this version.";
        private const string VersionPrefix = "Version ";

        [MenuItem(MenuPath, false, MenuPriority)]
        private static void OpenWindow()
        {
            AvatarDoctorWindow window = GetWindow<AvatarDoctorWindow>();
            window.titleContent = new GUIContent(AvatarDoctorPackageInfo.DisplayName);
            window.minSize = new Vector2(MinimumWidth, MinimumHeight);
            window.Show();
        }

        private void OnEnable()
        {
            titleContent = new GUIContent(AvatarDoctorPackageInfo.DisplayName);
            minSize = new Vector2(MinimumWidth, MinimumHeight);
        }

        public void CreateGUI()
        {
            VisualElement root = rootVisualElement;
            rootVisualElement.Clear();

            root.style.flexDirection = FlexDirection.Column;
            root.style.flexGrow = 1;
            root.style.paddingTop = 16;
            root.style.paddingRight = 16;
            root.style.paddingBottom = 16;
            root.style.paddingLeft = 16;

            VisualElement content = new VisualElement();
            content.style.flexDirection = FlexDirection.Column;
            content.style.flexGrow = 1;

            Label heading = new Label(AvatarDoctorPackageInfo.DisplayName);
            heading.style.fontSize = 20;
            heading.style.unityFontStyleAndWeight = FontStyle.Bold;
            heading.style.whiteSpace = WhiteSpace.Normal;
            heading.style.marginBottom = 8;
            content.Add(heading);

            Label status = new Label(StatusText);
            status.style.unityFontStyleAndWeight = FontStyle.Bold;
            status.style.whiteSpace = WhiteSpace.Normal;
            status.style.marginBottom = 8;
            content.Add(status);

            Label unavailableAnalysis = new Label(UnavailableAnalysisMessage);
            unavailableAnalysis.style.whiteSpace = WhiteSpace.Normal;
            unavailableAnalysis.style.marginBottom = 8;
            content.Add(unavailableAnalysis);

            Label version = new Label(VersionPrefix + AvatarDoctorPackageInfo.Version);
            version.style.whiteSpace = WhiteSpace.Normal;
            content.Add(version);

            root.Add(content);
        }
    }
}
