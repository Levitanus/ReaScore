# import reapy as rpr
# from reapy import ImGui

# # rpr.get_

# ctx = ImGui.CreateContext('ReaScore')

# tonics = ['c', 'cis', 'd', 'dis']
# tonic_selected = 0

# def main():
#     if ImGui.TreeNode(ctx, 'main'):
#         global tonic_selected
#         if ImGui.BeginCombo(ctx, 'tonic', tonics[tonic_selected]):
#             for idx, tonic in enumerate(tonics):
#                 _, selected = ImGui.Selectable(
#                     ctx, tonics[idx], tonic_selected == idx
#                 )
#                 if selected:
#                     tonic_selected = idx

#             ImGui.EndCombo(ctx)
#         ImGui.TreePop(ctx)

# def loop():
#     visible, open_ = ImGui.Begin(ctx, 'ReaScore Inspector', True)
#     if visible:
#         ImGui.Text(ctx, 'Hello World!')
#         main()
#         ImGui.End(ctx)

#     if open_:
#         rpr.defer(loop)
#     else:
#         ImGui.DestroyContext(ctx)

# rpr.defer(loop)
