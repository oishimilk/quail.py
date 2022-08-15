"""
Blender で MMD モデルを作るお手伝いをします。
Copyright (C) 2017-2022 Quail (oishimilk). Some rights reserved.

Compatible with Blender 3.2.2 and mmd_tools v2.4.0
"""
import csv
import sys
import platform

from typing import Iterable, Sequence, Union
from datetime import datetime

import bpy
import mmd_tools

# バージョン
VERSION = (0, 2, 0)


def _select_armature() -> bpy.types.Object:
	"""
	現在の Blender シーン中で最初に見つかった Armature を返します。
	シーンあたり1体のモデルが存在することを前提としています。

	@return: (bpy_types.Object) Armature
	"""
	for obj in bpy.context.scene.objects:
		if obj.mmd_type == 'ROOT':
			for child in obj.children:
				if child.type == 'ARMATURE':
					return child

	raise RuntimeError("Armature が見つかりませんでした。")


def _select_root() -> bpy.types.Object:
	"""
	現在の Blender シーン中で最初に見つかった MMD Root オブジェクト を返します。
	シーンあたり1体のモデルが存在することを前提としています。

	@return: (bpy_types.Object) MMD Root
	"""
	for obj in bpy.context.scene.objects:
		if obj.mmd_type == 'ROOT':
			return obj

	raise RuntimeError("MMD Root オブジェクトが見つかりませんでした。")


def set_japanese_bone_names() -> None:
	"""
	Blender用ボーン名を使ってMMD用日本語ボーン名を割り当てます。

	- `mmd_tools`側にもすでに同様の機能があるので廃止予定です。
	- `excluded`ボーンのみ個別対応が必要なため残しています。
	"""
	# 以下のボーンは処理されません。
	excluded = ("上半身2補助.L", "上半身2補助.R", "腰キャンセル.L", "腰キャンセル.R", "下半身補助.L", "下半身補助.R")

	for bone in _select_armature().pose.bones:
		if bone.is_mmd_shadow_bone:
			continue

		if bone.name in excluded:
			print(bone.name + " (MMD名: %s) の処理を飛ばします" % bone.mmd_bone.name_j)
			continue

		if ".L" in bone.name:
			bone.mmd_bone.name_j = "左" + bone.name.replace(".L", "")
		elif ".R" in bone.name:
			bone.mmd_bone.name_j = "右" + bone.name.replace(".R", "")
		else:
			bone.mmd_bone.name_j = bone.name

		print("%s を設定しました。" % bone.name)


def set_english_bone_names(overwrite: bool = False) -> None:
	"""
	MMD用日本語ボーン名を翻訳してMMD用英語ボーン名を割り当てます。
	先に`set_japanese_bone_names()`を実行してください。
	`mmd_tools`側にもすでに同様の機能があるので廃止予定です。

	@param overwrite: (bool) [任意] 設定済みの名前を上書きするかどうか
	"""
	for bone in _select_armature().pose.bones:
		if bone.is_mmd_shadow_bone:
			continue

		english_name = mmd_tools.translations.translateFromJp(bone.mmd_bone.name_j)

		if not(english_name.replace("_", "").encode('utf-8').isalnum()):
			print("※%sは残念ながら辞書に登録がありませんでした。飛ばします。" % bone.name)
		else:
			if bone.mmd_bone.name_e != "" and not(overwrite):
				print("※%sの設定を飛ばします。" % bone.name)
			else:
				bone.mmd_bone.name_e = english_name
				print("%sの英名として%sを登録しました。" % (bone.name, english_name))


def show_bone_identifier() -> None:
	"""
	ID が割り当てられているボーンを表示します。
	"""
	for bone in _select_armature().pose.bones:
		if bone.mmd_bone.bone_id != -1:
			print("ID: %d 名前: %s" % (bone.mmd_bone.bone_id, bone.name))


def check_invalid_bone_name() -> None:
	"""
	無効な名前をもつボーンがないか確認します。
	"""
	for bone in _select_armature().pose.bones:
		if bone.is_mmd_shadow_bone:
			continue

		if bone.mmd_bone.name_e == "":
			print("%s は英語名が空です!" % bone.name)
		elif not(bone.mmd_bone.name_e.replace("_", "").replace("+", "").encode('utf-8').isalnum()):
			print("%s は英語名が変です!" % bone.name)

		if bone.mmd_bone.name_j == "":
			print("%s は日本語名が空です!" % bone.name)
		elif ".L" in bone.name:
			if bone.mmd_bone.name_j != "左" + bone.name.replace(".L", ""):
				print("Blender用(%s)とMMD用(%s)で名称が異なっています!" % (bone.name, bone.mmd_bone.name_j))
		elif ".R" in bone.name:
			if bone.mmd_bone.name_j != "右" + bone.name.replace(".R", ""):
				print("Blender用(%s)とMMD用(%s)で名称が異なっています!" % (bone.name, bone.mmd_bone.name_j))
		else:
			if bone.mmd_bone.name_j != bone.name:
				print("Blender用(%s)とMMD用(%s)で名称が異なっています!" % (bone.name, bone.mmd_bone.name_j))


def check_bone_panel(root_obj: Union[None, bpy.types.Object] = None) -> None:
	"""
	表示パネルに登録されているボーンを選択することで、未登録のボーンをあぶり出します。

	@param root_obj: (None | bpy.types.Object) [任意] MMD モデルのルート
	"""
	if root_obj is None:
		root_obj = _select_root()
		bones = _select_armature().pose.bones
	else:
		for obj in root_obj.children:
			if obj.type == 'ARMATURE':
				bones = obj.pose.bones
				break
		else:
			raise RuntimeError("Armature が見つかりませんでした。")

	for frame in root_obj.mmd_root.display_item_frames:
		for item in frame.items:
			if item.name in bones:
				bones[item.name].bone.select = True

	print("現在選択されていないボーンは表示パネルに未登録です。")


def set_morph_panel(root_obj: Union[None, bpy.types.Object] = None) -> None:
	"""
	表示パネルにモーフを設定します。

	@param root_obj: (None | bpy.types.Object) [任意] MMD モデルのルート
	"""
	processed_list = []

	if root_obj is None:
		root_obj = _select_root()

	for i in root_obj.mmd_root.display_item_frames['表情'].items:
		processed_list.append(i.name)

	for keycolle in bpy.data.shape_keys:
		# 最初のキーブロックはベース (Basis) なので飛ばします。
		for shape in keycolle.key_blocks[1:]:
			if shape.name in processed_list:
				print(shape.name + " はすでに処理済みです! 二重登録を防止するために中断します。")
				continue

			temp = root_obj.mmd_root.display_item_frames['表情'].items.add()
			temp.type = 'MORPH'
			temp.name = shape.name
			temp = root_obj.mmd_root.vertex_morphs.add()
			temp.name = shape.name

			processed_list.append(shape.name)
			print("%s を登録しました。" % shape.name)


def set_english_morph_names(root_obj: Union[None, bpy.types.Object] = None, csv_file: str = "//../CommonMorphList.csv", overwrite: bool = True) -> None:
	"""
	英語のモーフ名を設定します。
	`mmd_tools`側に同等の機能があるため、廃止予定です。

	@param root_obj: (None | bpy.types.Object) [任意] MMD モデルのルート
	@param csv_file: (str) [任意] 設定に用いる辞書
	@param overwrite: (bool) [任意] 設定済みの名前を上書きするかどうか
	"""
	with open(bpy.path.abspath(csv_file), "r") as f:
		reader = csv.reader(f)

		for morph_dict in reader:
			morph_name_ja, morph_name_en = morph_dict

			if morph_name_ja in root_obj.mmd_root.vertex_morphs:
				morph = root_obj.mmd_root.vertex_morphs[morph_name_ja]

				if not overwrite and morph.name_e != "":
					print("※ %s の設定を飛ばします。" % morph.name)
				else:
					morph.name_e = morph_name_en
					print("%s の英名 %s を登録しました。" % (morph_name_ja, morph_name_en))
			else:
				print("%s: このモデルにそのようなモーフはありません。" % morph_name_ja)


def set_english_rigid_names(overwrite: bool = False) -> None:
	"""
	英語の剛体名を設定します。
	`mmd_tools`側に同等の機能があるため廃止予定です。

	@param overwrite: (bool) [任意] 設定済みの名前を上書きするかどうか
	"""
	for obj in bpy.context.scene.objects:
		if obj.mmd_type != 'RIGID_BODY':
			continue

		english_name = mmd_tools.translations.translateFromJp(obj.mmd_rigid.name_j)

		if english_name.replace("_", "").encode('utf-8').isalnum():
			if not overwrite and obj.mmd_rigid.name_e != "":
				print("※ %s の設定を飛ばします。" % obj.mmd_rigid.name_j)
			else:
				obj.mmd_rigid.name_e = english_name
				print("%s の英名として %s を登録しました。" % (obj.mmd_rigid.name_j, english_name))
		else:
			print("!!! %s は残念ながら辞書に登録がありませんでした。飛ばします。" % obj.mmd_rigid.name_j)
			continue


def set_english_joint_names(overwrite: bool = False) -> None:
	"""
	関節の剛体名を設定します。
	`mmd_tools`側に同等の機能があるため廃止予定です。

	@param overwrite: (bool) [任意] 設定済みの名前を上書きするかどうか
	"""
	for obj in bpy.context.scene.objects:
		if obj.mmd_type != 'JOINT':
			continue

		english_name = mmd_tools.translations.translateFromJp(obj.mmd_joint.name_j)

		if english_name.replace("_", "").encode('utf-8').isalnum():
			if not overwrite and obj.mmd_joint.name_e != "":
				print("※ %s の設定を飛ばします。" % obj.mmd_joint.name_j)
			else:
				obj.mmd_joint.name_e = english_name
				print("%s の英名として %s を登録しました。" % (obj.mmd_joint.name_j, english_name))
		else:
			print("!!! %s は残念ながら辞書に登録がありませんでした。飛ばします。" % obj.mmd_joint.name_j)
			continue


def check_physics_name_duplication_in_mmd() -> None:
	"""
	剛体・関節名が重複していないか確認します。
	"""
	rigids = []
	joints = []

	for obj in bpy.context.scene.objects:
		if obj.mmd_type == 'JOINT':
			joints.append(obj.mmd_joint.name_j)

		if obj.mmd_type == 'RIGID_BODY':
			rigids.append(obj.mmd_rigid.name_j)

	physics = rigids + joints

	for name in physics:
		if physics.count(name) > 2:
			print("%s の名称が重複しています!" % name)


def process_tip_bones_for_mmd() -> None:
	"""
	先ボーンを設定します。
	"""
	arm = _select_armature()

	for bone in arm.pose.bones:
		if bone.mmd_bone.name_j.endswith("先"):
			bone.mmd_bone.is_tip = True
			arm.data.bones[bone.name].hide = True
			print("%s を先ボーンに設定しました。" % bone.name)


def select_this_obj_only(obj: bpy.types.Object) -> None:
	"""
	指定したオブジェクトのみを選択状態にします。
	止まる場合は、そのオブジェクトが所属するレイヤが表示されているか確認してください。

	@param obj: (bpy.types.Object) [必須] 選択するオブジェクト
	"""
	bpy.ops.object.select_all(action='DESELECT')
	obj.hide = False
	obj.select = True
	bpy.context.active_object = obj

	# 強制オブジェクトモード
	bpy.ops.object.mode_set(mode='OBJECT', toggle=False)

	print("%s を選択しました。" % obj)


def apply_shape_as_basis(obj: bpy.types.Object, shape_name: Union[str, Sequence[str]], blend: float = 1.0) -> bpy.types.Object:
	"""
	指定したモーフを基準状態として登録します。

	@param obj: (bpy.types.Object) [必須] 編集するオブジェクト
	@param shape_name: (str | [str]) [必須] 適用するシェイプキーの名前
	@param blend: (float) [任意] 元の状態に適用するシェイプキーをどのくらい混ぜるか
	@return: (bpy.types.Object) シェイプキーが適用されたオブジェクト
	"""
	select_this_obj_only(obj)
	bpy.ops.object.duplicate_move() # 退避

	bpy.ops.object.mode_set(mode='EDIT')

	bpy.context.object.active_shape_key_index = 0 # ベース
	bpy.ops.mesh.select_all(action='SELECT')

	if type(shape_name) is str:
		if shape_name in bpy.context.active_object.data.shape_keys.key_blocks:
			bpy.ops.mesh.blend_from_shape(shape=shape_name, add=False, blend=blend)
			print("%s に %s を基準状態として登録しました。" % (obj, shape_name))
		else:
			print("警告: %s に %s というキーは存在しません。何も行いません。" % (obj, shape_name))
	else:
		for shp in shape_name:
			if shp in bpy.context.active_object.data.shape_keys.key_blocks:
				bpy.ops.mesh.blend_from_shape(shape=shp, add=False, blend=blend)
				bpy.ops.object.mode_set(mode='OBJECT')
				bpy.ops.object.mode_set(mode='EDIT')
				print("%s を基準状態として登録しました。" % shp)
			else:
				print("警告: %s に %s というキーは存在しません。何も行いません。" % (obj, shp))

	bpy.ops.object.mode_set(mode='OBJECT')

	return bpy.context.active_object


def toggle_legs_ik(mode: bool) -> None:
	"""
	足 IK の有効/無効を切り替えます。

	@param mode: (bool) [必須] `True`で足 IK を有効に、`False`で無効にします。
	"""
	bones = ("ひざ.L", "ひざ.R", "足首.L", "足首.R")

	for bone in bones:
		_select_armature().pose.bones[bone].constraints["IK"].mute = not mode

	print("足 IK の %s への切り替えが完了しました。" % mode)


def update_pmx_comment(mmd_root: mmd_tools.properties.MMDRoot, identifier: Union[str, None] = None, mm_ver: Union[Sequence[int], None] = None, copyright_jp: Union[str, None] = None, copyright_en: Union[str, None] = None, pname: Union[str, None] = None, additional_jp: Union[str, None] = None, additional_en: Union[str, None] = None) -> None:
	"""
	PMX ファイルに埋め込まれるメタデータを更新します。
	モジュールを呼び出した Blender ファイルと同じフォルダに`changelog`が存在している必要があります。

	@param mmd_root: (mmd_tools.properties.MMDRoot) [必須] モデルのルート
	@param identifier: (str) [任意] モデルの changelog 内における識別子(リビジョンの取得に使います)
	@param mm_ver: ((int)) [任意] Model Manipulator (mm.py) のバージョン
	@param copyright_jp: (str) [任意] 著作権に関する情報(日本語)
	@param copyright_en: (str) [任意] 著作権に関する情報(英語)
	@param pname: (str) [任意] モデルが属する何らかの大規模プロジェクト
	@param additional_jp: (str) [任意] 追加情報(日本語)
	@param additional_en: (str) [任意] 追加情報(英語)
	"""
	# コメントが指定されていない場合は例外を発します。
	assert mmd_root.comment_text
	assert mmd_root.comment_e_text

	# コメント用テキストブロック確保
	comment_jp = bpy.data.texts[mmd_root.comment_text]
	comment_en = bpy.data.texts[mmd_root.comment_e_text]

	# 初期化
	comment_jp.clear()
	comment_en.clear()

	# モデル名
	comment_jp.write("%s\n" % mmd_root.name)
	comment_en.write("%s\n" % mmd_root.name_e)

	# 著作権表示
	if copyright_jp is not None:
		comment_jp.write("%s\n" % copyright_jp)

	if copyright_en is not None:
		comment_en.write("%s\n" % copyright_en)

	# ビルド情報
	comment_jp.write("\nビルド情報")
	comment_en.write("\nBuild Information")

	# リビジョン
	if identifier is None:
		comment_jp.write("\n")
		comment_en.write("\n")
	else:
		with open(bpy.path.abspath("//changelog")) as f:
			changelog = f.read()

		SEARCH_STRING = "\t* %s (r" % identifier

		start = changelog.rfind(SEARCH_STRING) + len(SEARCH_STRING)
		end = changelog.find("):", start)

		comment_jp.write(" (リビジョン%s)\n" % changelog[start:end])
		comment_en.write(" (Revision %s)\n" % changelog[start:end])

	# プロジェクト
	if pname is not None:
		comment_jp.write("project:\t%s\n" % pname)
		comment_en.write("project:\t%s\n" % pname)

	def iter2str(iterable: Iterable, split: str = ".") -> str:
		"""
		iterable を 結合して str に変換します。

		@param iterable: (iterable) [必須] 繰り返し可能なオブジェクト ex. (2, 79, 0)
		@param split: (str) [任意] 区切り文字
		@return cat: (str) 結合された文字列 ex. 2.79.0
		"""
		cat = ""

		for i in iterable:
			cat += "%s%s" % (i, split)

		return cat[:-1]

	# モデル生成に使用したソフトウェアのバージョン
	version_signature = "Blender v%s, mmd_tools v%s, quail.py v%s" % (iter2str(bpy.app.version), iter2str(mmd_tools.bl_info["version"]), iter2str(VERSION))

	# mm.py
	if mm_ver is not None:
		version_signature += ", mm.py v%s" % iter2str(mm_ver)

	comment_jp.write("builder:\t%s\n" % version_signature)
	comment_en.write("builder:\t%s\n" % version_signature)

	# モデル生成に使用したプラットフォーム
	uname = platform.uname()
	comment_jp.write("platform:\t%s %s (%s) @%s\n" % (uname.system, uname.release, uname.machine, uname.node))
	comment_en.write("platform:\t%s %s (%s) @%s\n" % (uname.system, uname.release, uname.machine, uname.node))

	# タイムスタンプ
	now = datetime.now()
	comment_jp.write("timestamp:\t%s (現地時間)\n" % now)
	comment_en.write("timestamp:\t%s (local time)\n" % now)

	# コマンドライン引数
	comment_jp.write("command:\t%s\n" % iter2str(sys.argv, split=" "))
	comment_en.write("command:\t%s\n" % iter2str(sys.argv, split=" "))

	# 追加情報
	if additional_jp is not None:
		comment_jp.write("\n追加情報\n%s" % additional_jp)

	if additional_en is not None:
		comment_en.write("\nAdditional Information\n%s" % additional_en)

	print("メタデータを更新しました。")


def switch_layers(enable: Sequence[int] = [0]) -> None:
	"""
	Switch scene layers.

	@param enable: [optional] ([int]) Layers enabled.
	"""
	# レイヤーではない
	layers = bpy.context.scene.collection.children

	for i, layer in enumerate(layers):
		layer.hide_viewport = i not in enable
		layer.hide_render = i not in enable

	print("可視レイヤの切り替えが完了しました。")


def multiply_mass(mul: float, parent: bpy.types.Object) -> None:
	"""
	物理演算の Blender-MMD 間のつじつまを合わせるために、剛体の質量に定数を乗じます。
	MMD は初期状態で Blender の10倍の重力加速度が設定されているようです。

	@param mul: (float) [必須] 質量の倍数
	@param parent: (bpy.types.Object) [必須] 剛体の親。通常、`rigidbodies`です。
	"""
	assert parent.mmd_type == 'RIGID_GRP_OBJ'

	for obj in parent.children:
		obj.rigid_body.mass *= mul

	print("剛体の質量を %f 倍しました。" % mul)


def toggle_subsurf(mode: bool, target: Union[None, Sequence[bpy.types.Modifier]] = None, mod_type: Sequence[str] = ('SUBSURF')) -> Sequence[bpy.types.Modifier]:
	"""
	細分割曲面モディファイアおよび他のモディファイアの有効・無効を切り替えます。

	@param mode: (bool) [必須]
		有効にするか(`True`) 無効にするか(`False`)
	@param target: ([bpy.types.Modifier]) [任意]
		対象とするモディファイアのリストです。指定した場合、`mod_type`は無視されます。
		未指定の場合、すべてのオブジェクトに設定された`mod_type`に該当するモディファイアを対象とします。
	@param mod_type: ((str)) [任意]
		切り替えるモディファイアのタイプ
	@return toggled: ([bpy.types.Modifier])
		切り替えたモディファイアのリスト
	"""
	toggled = []

	if target is None:
		for obj in bpy.context.scene.objects:
			for mod in obj.modifiers:
				if mod.type in mod_type:
					if mod.show_viewport != mode:
						mod.show_viewport = mode
						toggled.append(mod)
	else:
		for mod in target:
			if mod.show_viewport != mode:
				mod.show_viewport = mode
				toggled.append(mod)

	print("モディファイア %s を %s にしました。" % (mod_type, mode))

	return toggled


def delete_vertex_group(obj: bpy.types.Object, group_name: Sequence[str]) -> bpy.types.Object:
	"""
	指定されたオブジェクトの指定された頂点グループに属する頂点を削除します。
	軽量版の生成に用いられます。

	@param obj (bpy.types.Object): [必須] 対象とするオブジェクト
	@param group_name ([str]): [必須] 削除する頂点グループ名のリスト
	@return obj (bpy.types.Object): 指定の頂点が削除されたオブジェクト
	"""
	select_this_obj_only(obj)

	bpy.ops.object.duplicate_move() # 退避

	obj = bpy.context.active_object

	bpy.ops.object.mode_set(mode='EDIT')
	bpy.ops.mesh.select_all(action='DESELECT')
	bpy.ops.object.mode_set(mode='OBJECT')

	for vertex in obj.data.vertices:
		for group in vertex.groups:
			if obj.vertex_groups[group.group].name in group_name:
				vertex.select = True
				break

	bpy.ops.object.mode_set(mode='EDIT')
	bpy.ops.mesh.delete(type='VERT')
	bpy.ops.object.mode_set(mode='OBJECT')

	print("%s の %s に属する頂点を削除しました。" % (obj, group_name))

	return obj


"""
Then what would you like to do?
Type "quail = bpy.data.texts['quail.py'].as_module()" and quail.<function> in the console.
If you need help, type "help(quail)" in the console.
"""
