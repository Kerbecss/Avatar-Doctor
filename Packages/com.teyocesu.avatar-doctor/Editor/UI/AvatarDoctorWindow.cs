using System;
using System.Collections.Generic;
using Teyocesu.AvatarDoctor.Editor.Core;
using Teyocesu.AvatarDoctor.Editor.Discovery;
using Teyocesu.AvatarDoctor.Editor.Selection;
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
        private const string RefreshText = "Refresh";
        private const string NoAvatarMessage =
            "No VRChat Avatar Descriptors found in the loaded scene(s).";
        private const string OneAvatarMessage =
            "1 VRChat Avatar Descriptor found and selected automatically.";
        private const string MultipleAvatarMessageFormat =
            "{0} VRChat Avatar Descriptors found.";
        private const string ChooseAvatarText = "Choose an avatar...";
        private const string SelectionRequiredMessage =
            "No avatar selected automatically. Choose an avatar.";
        private const string VersionPrefix = "Version ";

        private AvatarDoctorWindowController controller;
        private VisualElement stateContainer;
        private Button refreshButton;

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
            if (controller != null)
            {
                controller.Dispose();
            }

            controller = new AvatarDoctorWindowController(
                new UnityAvatarDoctorEditorEventSource(),
                Render);
            controller.Enable();
        }

        private void OnDisable()
        {
            if (controller != null)
            {
                controller.Dispose();
                controller = null;
            }

            stateContainer = null;
            refreshButton = null;
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

            Label heading = new Label(AvatarDoctorPackageInfo.DisplayName);
            heading.style.fontSize = 20;
            heading.style.unityFontStyleAndWeight = FontStyle.Bold;
            heading.style.whiteSpace = WhiteSpace.Normal;
            heading.style.marginBottom = 8;
            root.Add(heading);

            refreshButton = new Button(HandleExplicitRefresh)
            {
                text = RefreshText,
            };
            refreshButton.style.marginBottom = 8;
            root.Add(refreshButton);

            stateContainer = new VisualElement();
            stateContainer.style.flexDirection = FlexDirection.Column;
            stateContainer.style.flexGrow = 1;
            root.Add(stateContainer);

            Label version = new Label(VersionPrefix + AvatarDoctorPackageInfo.Version);
            version.style.whiteSpace = WhiteSpace.Normal;
            version.style.marginTop = 8;
            root.Add(version);

            Render();
        }

        internal static IReadOnlyList<string> BuildCandidateLabels(
            IReadOnlyList<AvatarDiscoveryCandidate> candidates)
        {
            List<string> labels = new List<string>();
            for (int index = 0; index < candidates.Count; index++)
            {
                labels.Add(BuildCandidateLabel(candidates[index], candidates));
            }

            return labels;
        }

        private void HandleExplicitRefresh()
        {
            if (controller != null)
            {
                controller.RefreshExplicit();
            }
        }

        private void Render()
        {
            if (stateContainer == null || controller == null)
            {
                return;
            }

            stateContainer.Clear();
            if (!string.IsNullOrEmpty(controller.TransientOperationalError))
            {
                AddLabel(
                    stateContainer,
                    controller.TransientOperationalError,
                    true);
            }

            AvatarDiscoveryResult result = controller.DiscoveryResult;
            switch (result.CountState)
            {
                case AvatarDiscoveryState.None:
                    RenderNoAvatars();
                    break;
                case AvatarDiscoveryState.Single:
                    RenderOneAvatar(result);
                    break;
                case AvatarDiscoveryState.Multiple:
                    RenderMultipleAvatars(result);
                    break;
                default:
                    throw new ArgumentOutOfRangeException();
            }
        }

        private void RenderNoAvatars()
        {
            AddLabel(stateContainer, NoAvatarMessage, true);
        }

        private void RenderOneAvatar(AvatarDiscoveryResult result)
        {
            AddLabel(stateContainer, OneAvatarMessage, true);
            AddSelectedCandidateDetails(
                stateContainer,
                controller.CurrentSelection,
                result.Candidates);
        }

        private void RenderMultipleAvatars(AvatarDiscoveryResult result)
        {
            AddLabel(
                stateContainer,
                string.Format(
                    MultipleAvatarMessageFormat,
                    result.Candidates.Count),
                true);

            IReadOnlyList<string> candidateLabels = BuildCandidateLabels(
                result.Candidates);
            List<string> choices = new List<string> { ChooseAvatarText };
            for (int index = 0; index < candidateLabels.Count; index++)
            {
                choices.Add(candidateLabels[index]);
            }

            int selectedIndex = FindSelectedCandidateIndex(
                result,
                controller.CurrentSelection);
            DropdownField selector = new DropdownField(
                "Select avatar",
                choices,
                selectedIndex < 0 ? 0 : selectedIndex + 1);
            selector.style.marginBottom = 8;
            selector.RegisterValueChangedCallback(change =>
            {
                int candidateIndex = choices.IndexOf(change.newValue) - 1;
                if (candidateIndex >= 0
                    && candidateIndex < result.Candidates.Count)
                {
                    controller.TrySelectManual(result.Candidates[candidateIndex]);
                }
            });
            stateContainer.Add(selector);

            if (controller.CurrentSelection.State
                == AvatarSelectionState.Selected)
            {
                AddSelectedCandidateDetails(
                    stateContainer,
                    controller.CurrentSelection,
                    result.Candidates);
            }
            else
            {
                AddLabel(stateContainer, SelectionRequiredMessage, true);
            }
        }

        private static int FindSelectedCandidateIndex(
            AvatarDiscoveryResult result,
            AvatarSelection selection)
        {
            if (selection.State != AvatarSelectionState.Selected)
            {
                return -1;
            }

            for (int index = 0; index < result.Candidates.Count; index++)
            {
                if (ReferenceEquals(result.Candidates[index], selection.Candidate))
                {
                    return index;
                }
            }

            return -1;
        }

        private static void AddSelectedCandidateDetails(
            VisualElement container,
            AvatarSelection selection,
            IReadOnlyList<AvatarDiscoveryCandidate> candidates)
        {
            if (selection.State != AvatarSelectionState.Selected)
            {
                return;
            }

            AvatarDiscoveryCandidate candidate = selection.Candidate;
            AddLabel(
                container,
                "Selected avatar: " + BuildCandidateLabel(candidate, candidates),
                true);
            AddLabel(container, "GameObject: " + candidate.DisplayName);
            AddLabel(container, "Hierarchy: " + candidate.HierarchyDisplayPath);
            AddLabel(container, "Scene: " + candidate.SceneIdentity);
            AddLabel(
                container,
                "Selection origin: " + FormatSelectionOrigin(selection.Origin));
        }

        private static string BuildCandidateLabel(
            AvatarDiscoveryCandidate candidate,
            IReadOnlyList<AvatarDiscoveryCandidate> candidates)
        {
            string label = string.Format(
                "{0} — {1} — {2}",
                candidate.DisplayName,
                candidate.SceneIdentity,
                candidate.HierarchyDisplayPath);
            if (NeedsDescriptorOrdinal(candidate, candidates))
            {
                label = label + string.Format(
                    " — Descriptor {0}",
                    candidate.DescriptorComponentOrdinal + 1);
            }

            return label;
        }

        private static bool NeedsDescriptorOrdinal(
            AvatarDiscoveryCandidate candidate,
            IReadOnlyList<AvatarDiscoveryCandidate> candidates)
        {
            for (int index = 0; index < candidates.Count; index++)
            {
                AvatarDiscoveryCandidate other = candidates[index];
                if (ReferenceEquals(candidate, other))
                {
                    continue;
                }

                if (candidate.AvatarRoot == other.AvatarRoot
                    && string.Equals(
                        candidate.DisplayName,
                        other.DisplayName,
                        StringComparison.Ordinal)
                    && string.Equals(
                        candidate.SceneIdentity,
                        other.SceneIdentity,
                        StringComparison.Ordinal)
                    && string.Equals(
                        candidate.HierarchyDisplayPath,
                        other.HierarchyDisplayPath,
                        StringComparison.Ordinal))
                {
                    return true;
                }
            }

            return false;
        }

        private static string FormatSelectionOrigin(
            AvatarSelectionOrigin? origin)
        {
            if (!origin.HasValue)
            {
                return "Unresolved";
            }

            switch (origin.Value)
            {
                case AvatarSelectionOrigin.Manual:
                    return "Manual";
                case AvatarSelectionOrigin.AutomaticSingle:
                    return "Automatic — sole candidate";
                case AvatarSelectionOrigin.AutomaticEditorSelection:
                    return "Automatic — active Editor selection";
                default:
                    throw new ArgumentOutOfRangeException(nameof(origin));
            }
        }

        private static void AddLabel(
            VisualElement container,
            string text,
            bool bold = false)
        {
            Label label = new Label(text);
            label.style.whiteSpace = WhiteSpace.Normal;
            label.style.marginBottom = 8;
            if (bold)
            {
                label.style.unityFontStyleAndWeight = FontStyle.Bold;
            }

            container.Add(label);
        }
    }
}
