using System;
using Teyocesu.AvatarDoctor.Editor.Discovery;
using Teyocesu.AvatarDoctor.Editor.Selection;
using UnityEditor;
using UnityEditor.SceneManagement;
using UnityEngine;
using UnityEngine.SceneManagement;
using UnityObject = UnityEngine.Object;
using UnityEditorSelection = UnityEditor.Selection;

namespace Teyocesu.AvatarDoctor.Editor.UI
{
    internal interface IAvatarDoctorEditorEventSource : IDisposable
    {
        event Action HierarchyChanged;

        event Action SceneOpened;

        event Action SceneClosed;

        event Action SelectionChanged;

        UnityObject ActiveEditorSelection { get; }

        void ScheduleDelayCall(Action callback);

        void CancelDelayCall(Action callback);
    }

    internal sealed class AvatarDoctorWindowController : IDisposable
    {
        private readonly IAvatarDoctorEditorEventSource eventSource;
        private readonly Func<AvatarDiscoveryResult> discover;
        private readonly AvatarSelectionModel selectionModel;
        private readonly Action render;
        private readonly Action<string> logError;
        private bool isEnabled;
        private bool isDisposed;
        private bool refreshPending;
        private string transientOperationalError;

        internal AvatarDoctorWindowController(
            IAvatarDoctorEditorEventSource eventSource,
            Action render)
            : this(
                eventSource,
                new AvatarDiscoveryService().Discover,
                new AvatarSelectionModel(),
                render,
                message => Debug.LogError(message))
        {
        }

        internal AvatarDoctorWindowController(
            IAvatarDoctorEditorEventSource eventSource,
            Func<AvatarDiscoveryResult> discover,
            AvatarSelectionModel selectionModel,
            Action render,
            Action<string> logError)
        {
            this.eventSource = eventSource
                ?? throw new ArgumentNullException(nameof(eventSource));
            this.discover = discover
                ?? throw new ArgumentNullException(nameof(discover));
            this.selectionModel = selectionModel
                ?? throw new ArgumentNullException(nameof(selectionModel));
            this.render = render
                ?? throw new ArgumentNullException(nameof(render));
            this.logError = logError
                ?? throw new ArgumentNullException(nameof(logError));
        }

        internal AvatarDiscoveryResult DiscoveryResult =>
            selectionModel.DiscoveryResult;

        internal AvatarSelection CurrentSelection =>
            selectionModel.CurrentSelection;

        internal string TransientOperationalError => transientOperationalError;

        internal bool IsRefreshPending => refreshPending;

        internal bool IsEnabled => isEnabled;

        internal void Enable()
        {
            ThrowIfDisposed();
            if (isEnabled)
            {
                Disable();
            }

            eventSource.HierarchyChanged -= HandleHierarchyChanged;
            eventSource.SceneOpened -= HandleSceneOpened;
            eventSource.SceneClosed -= HandleSceneClosed;
            eventSource.SelectionChanged -= HandleSelectionChanged;

            eventSource.HierarchyChanged += HandleHierarchyChanged;
            eventSource.SceneOpened += HandleSceneOpened;
            eventSource.SceneClosed += HandleSceneClosed;
            eventSource.SelectionChanged += HandleSelectionChanged;
            isEnabled = true;
            ScheduleRefresh();
        }

        internal void Disable()
        {
            if (isDisposed)
            {
                return;
            }

            eventSource.HierarchyChanged -= HandleHierarchyChanged;
            eventSource.SceneOpened -= HandleSceneOpened;
            eventSource.SceneClosed -= HandleSceneClosed;
            eventSource.SelectionChanged -= HandleSelectionChanged;
            CancelScheduledRefresh();
            isEnabled = false;
        }

        internal void RefreshExplicit()
        {
            if (!isEnabled)
            {
                return;
            }

            CancelScheduledRefresh();
            ExecuteRefresh(true);
        }

        internal bool TrySelectManual(AvatarDiscoveryCandidate candidate)
        {
            if (!isEnabled)
            {
                return false;
            }

            bool selected = false;
            try
            {
                selected = selectionModel.TrySelectManual(candidate);
            }
            catch (Exception exception)
            {
                RecordOperationalError("manual avatar selection", exception);
            }
            finally
            {
                render();
            }

            return selected;
        }

        public void Dispose()
        {
            if (isDisposed)
            {
                return;
            }

            Disable();
            eventSource.Dispose();
            isDisposed = true;
        }

        private void HandleHierarchyChanged()
        {
            ScheduleRefresh();
        }

        private void HandleSceneOpened()
        {
            ScheduleRefresh();
        }

        private void HandleSceneClosed()
        {
            ScheduleRefresh();
        }

        private void HandleSelectionChanged()
        {
            if (!isEnabled)
            {
                return;
            }

            try
            {
                selectionModel.ApplyEditorSelection(
                    eventSource.ActiveEditorSelection);
            }
            catch (Exception exception)
            {
                RecordOperationalError("Editor selection observation", exception);
            }
            finally
            {
                render();
            }
        }

        private void ScheduleRefresh()
        {
            if (!isEnabled || refreshPending)
            {
                return;
            }

            refreshPending = true;
            eventSource.ScheduleDelayCall(ExecuteScheduledRefresh);
        }

        private void CancelScheduledRefresh()
        {
            if (!refreshPending)
            {
                return;
            }

            eventSource.CancelDelayCall(ExecuteScheduledRefresh);
            refreshPending = false;
        }

        private void ExecuteScheduledRefresh()
        {
            refreshPending = false;
            if (isEnabled)
            {
                ExecuteRefresh(false);
            }
        }

        private void ExecuteRefresh(bool clearErrorOnSuccess)
        {
            try
            {
                AvatarDiscoveryResult result = discover();
                selectionModel.ApplyDiscoveryResult(
                    result,
                    eventSource.ActiveEditorSelection);
                if (clearErrorOnSuccess)
                {
                    transientOperationalError = null;
                }
            }
            catch (Exception exception)
            {
                RecordOperationalError("avatar discovery refresh", exception);
            }
            finally
            {
                render();
            }
        }

        private void RecordOperationalError(
            string operation,
            Exception exception)
        {
            transientOperationalError = string.Format(
                "Avatar Doctor: {0} failed. {1} Click Refresh to retry.",
                operation,
                exception.Message);
            logError(string.Format(
                "Avatar Doctor: {0} failed.\n{1}",
                operation,
                exception));
        }

        private void ThrowIfDisposed()
        {
            if (isDisposed)
            {
                throw new ObjectDisposedException(
                    nameof(AvatarDoctorWindowController));
            }
        }
    }

    internal sealed class UnityAvatarDoctorEditorEventSource
        : IAvatarDoctorEditorEventSource
    {
        private EditorApplication.CallbackFunction delayedCallback;
        private bool isDisposed;

        internal UnityAvatarDoctorEditorEventSource()
        {
            EditorApplication.hierarchyChanged += HandleHierarchyChanged;
            EditorSceneManager.sceneOpened += HandleSceneOpened;
            EditorSceneManager.sceneClosed += HandleSceneClosed;
            UnityEditorSelection.selectionChanged += HandleSelectionChanged;
        }

        public event Action HierarchyChanged;

        public event Action SceneOpened;

        public event Action SceneClosed;

        public event Action SelectionChanged;

        public UnityObject ActiveEditorSelection => UnityEditorSelection.activeObject;

        public void ScheduleDelayCall(Action callback)
        {
            if (callback == null)
            {
                throw new ArgumentNullException(nameof(callback));
            }

            CancelDelayCall(callback);
            EditorApplication.CallbackFunction unityCallback = null;
            unityCallback = () =>
            {
                EditorApplication.delayCall -= unityCallback;
                if (delayedCallback == unityCallback)
                {
                    delayedCallback = null;
                }

                callback();
            };
            delayedCallback = unityCallback;
            EditorApplication.delayCall += unityCallback;
        }

        public void CancelDelayCall(Action callback)
        {
            if (delayedCallback == null)
            {
                return;
            }

            EditorApplication.delayCall -= delayedCallback;
            delayedCallback = null;
        }

        public void Dispose()
        {
            if (isDisposed)
            {
                return;
            }

            EditorApplication.hierarchyChanged -= HandleHierarchyChanged;
            EditorSceneManager.sceneOpened -= HandleSceneOpened;
            EditorSceneManager.sceneClosed -= HandleSceneClosed;
            UnityEditorSelection.selectionChanged -= HandleSelectionChanged;
            CancelDelayCall(null);
            HierarchyChanged = null;
            SceneOpened = null;
            SceneClosed = null;
            SelectionChanged = null;
            isDisposed = true;
        }

        private void HandleHierarchyChanged()
        {
            HierarchyChanged?.Invoke();
        }

        private void HandleSceneOpened(Scene scene, OpenSceneMode mode)
        {
            SceneOpened?.Invoke();
        }

        private void HandleSceneClosed(Scene scene)
        {
            SceneClosed?.Invoke();
        }

        private void HandleSelectionChanged()
        {
            SelectionChanged?.Invoke();
        }
    }
}
