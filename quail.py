"""
Blender で MMD モデルを作るお手伝いをします。
Copyright (C) 2017-2022 Quail (oishimilk). Some rights reserved.

Compatible with Blender 2.79 and mmd_tools v0.6.0
"""
import csv
import sys
import platform

from typing import Iterable, Sequence, Union
from datetime import datetime

import bpy

from mathutils import Euler

import mmd_tools

# バージョン
VERSION = (0, 1, 3)


def selectArmature() -> str:
	"""
	現在の Blender シーン中で最初に見つかった Armature 名を返します。

	@return: (str) Armature 名
	"""
	for obj in bpy.context.scene.objects:
		if obj.mmd_type == 'ROOT':
			for child in obj.children:
				if child.type == 'ARMATURE':
					return child.name

	raise RuntimeError("Armature が見つかりませんでした。")


def setJapaneseBoneNames() -> None:
	"""
	MMD 用日本語ボーン名を割り当てます。
	"""
	# 以下のボーンは処理されません。
	excluded = ("上半身2補助.L", "上半身2補助.R", "腰キャンセル.L", "腰キャンセル.R", "下半身補助.L", "下半身補助.R")

	for bone in bpy.data.objects[selectArmature()].pose.bones:
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


def setEnglishBoneNames(overwrite: bool = False) -> None:
	"""
	MMD 用英語ボーン名を割り当てます。
	先に`setJapaneseBoneNames()`を実行してください。

	@param overwrite: (bool) [任意] 設定済みの名前を上書きするかどうか
	"""
	for bone in bpy.data.objects[selectArmature()].pose.bones:
		if bone.is_mmd_shadow_bone:
			continue

		english_name = mmd_tools.translations.translateFromJp(bone.mmd_bone.name_j)

		if not(english_name.replace("_", "").encode('utf-8').isalnum()):
			print("※ %s は残念ながら辞書に登録がありませんでした。飛ばします。" % bone.name)
		else:
			if bone.mmd_bone.name_e != "" and not(overwrite):
				print("※ %s の設定を飛ばします。" % bone.name)
			else:
				bone.mmd_bone.name_e = english_name
				print("%s の英名として %s を登録しました。" % (bone.name, english_name))


def showBoneIdentifier() -> None:
	"""
	ID が割り当てられているボーンを表示します。
	"""
	for bone in bpy.data.objects[selectArmature()].pose.bones:
		if bone.mmd_bone.bone_id != -1:
			print("ID: %d 名前: %s" % (bone.mmd_bone.bone_id, bone.name))


def checkInvalidBoneName() -> None:
	"""
	無効な名前をもつボーンがないか確認します。
	"""
	for bone in bpy.data.objects[selectArmature()].pose.bones:
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


def checkBonePanel(model_name: str = bpy.context.scene.name) -> None:
	"""
	表示パネルに登録されているボーンを選択することで、未登録のボーンをあぶり出します。

	@param model_name: (str) [任意] MMD モデルに属するオブジェクトの名前
	"""
	bones = bpy.data.objects[selectArmature()].pose.bones

	for frame in bpy.data.objects[model_name].mmd_root.display_item_frames:
		for item in frame.items:
			if item.name in bones:
				bones[item.name].bone.select = True

	print("現在選択されていないボーンは表示パネルに未登録です。")


def setMorphPanel(model_name: str = bpy.context.scene.name) -> None:
	"""
	表示パネルにモーフを設定します。

	@param model_name: (str) [任意] MMD モデルに属するオブジェクトの名前
	"""
	processed_list = []

	for i in bpy.data.objects[model_name].mmd_root.display_item_frames['表情'].items:
		processed_list.append(i.name)

	for keycolle in bpy.data.shape_keys:
		# 最初のキーブロックはベース (Basis) なので飛ばします。
		for shape in keycolle.key_blocks[1:]:
			if shape.name in processed_list:
				print(shape.name + " はすでに処理済みです! 二重登録を防止するために中断します。")
				continue

			temp = bpy.data.objects[model_name].mmd_root.display_item_frames['表情'].items.add()
			temp.type = 'MORPH'
			temp.name = shape.name
			temp = bpy.data.objects[model_name].mmd_root.vertex_morphs.add()
			temp.name = shape.name

			processed_list.append(shape.name)
			print("%s を登録しました。" % shape.name)


def setEnglishMorphNames(target: str = bpy.context.scene.name, csv_file: str = "//../CommonMorphList.csv", overwrite: bool = True) -> None:
	"""
	英語のモーフ名を設定します。

	@param target: (str) [任意] MMD モデルに属するオブジェクトの名前
	@param csv_file: (str) [任意] 設定に用いる辞書
	@param overwrite: (bool) [任意] 設定済みの名前を上書きするかどうか
	"""
	with open(bpy.path.abspath(csv_file), "r") as f:
		reader = csv.reader(f)

		for morph_dict in reader:
			morph_name_ja, morph_name_en = morph_dict

			if morph_name_ja in bpy.data.objects[target].mmd_root.vertex_morphs:
				morph = bpy.data.objects[target].mmd_root.vertex_morphs[morph_name_ja]
				if not overwrite and morph.name_e != "":
					print("※ %s の設定を飛ばします。" % morph.name)
				else:
					morph.name_e = morph_name_en
					print("%s の英名 %s を登録しました。" % (morph_name_ja, morph_name_en))
			else:
				print("%s: このモデルにそのようなモーフはありません。" % morph_name_ja)


def setEnglishRigidNames(overwrite: bool = False) -> None:
	"""
	英語の剛体名を設定します。

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


def setEnglishJointNames(overwrite: bool = False) -> None:
	"""
	関節の剛体名を設定します。

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


def checkPhysicsDuplicationInMMD() -> None:
	"""
	剛体・関節が重複していないか確認します。
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


def processTipBonesForMMD() -> None:
	"""
	先ボーンを設定します。
	"""
	arm = bpy.data.objects[selectArmature()]

	for bone in arm.pose.bones:
		if bone.mmd_bone.name_j.endswith("先"):
			bone.mmd_bone.is_tip = True
			arm.data.bones[bone.name].hide = True
			print("%sを先ボーンに設定しました。" % bone.name)


def toggleNode(spec: bool) -> None:
	"""
	マテリアルノードを使用するか否かを設定します。
	レンダリングエンジンを設定してから呼び出してください。

	@param spec: (bool) [任意] マテリアルノードを使用するか否か
	"""
	use_cycles = bpy.context.scene.render.engine == "CYCLES"

	bpy.context.scene.render.use_stamp_memory = use_cycles

	if use_cycles:
		bpy.context.scene.render.stamp_note_text = bpy.context.scene.render.stamp_note_text.replace("Blender Internal Render", "Cycles Render")
	else:
		bpy.context.scene.render.stamp_note_text = bpy.context.scene.render.stamp_note_text.replace("Cycles Render", "Blender Internal Render")

	for material in bpy.data.materials:
		if "mmd_tools_rigid_" in material.name:
			continue

		material.use_nodes = spec

		print("%s のマテリアルノードの使用を %s に設定しました。" % (material.name, spec))


def updateOldPoseLib() -> None:
	"""
	2017 年以前に使われていたリグで作成されたポーズを更新します。
	廃止予定です。
	"""
	for fcurve in bpy.data.actions["PoseLib"].fcurves:
		if "左" in fcurve.data_path:
			fcurve.data_path = fcurve.data_path.replace("左", "").replace("\"]", ".L\"]")

		if "右" in fcurve.data_path:
			fcurve.data_path = fcurve.data_path.replace("右", "").replace("\"]", ".R\"]")

	print("ポーズの更新作業が完了しました。")


def toggleMorphLR() -> None:
	"""
	モーフの左右を標準と間違えて作っていた古いモデルを更新します。
	この関数を実行するとウィンクが壊れます。
	廃止予定です。
	"""
	for mesh in bpy.data.meshes:
		if hasattr(mesh.shape_keys, "key_blocks"):
			for key in mesh.shape_keys.key_blocks.keys():
				key_block = mesh.shape_keys.key_blocks[key]
				key_block.name = key_block.name.replace("左", "right")
				key_block.name = key_block.name.replace("右", "left")

			for key in mesh.shape_keys.key_blocks.keys():
				key_block = mesh.shape_keys.key_blocks[key]
				key_block.name = key_block.name.replace("left", "左")
				key_block.name = key_block.name.replace("right", "右")

	print("モーフの左右入れ替えが完了しました。ウィンクが壊れました。")


def selectThisObjOnly(obj_name: str) -> None:
	"""
	指定したオブジェクトのみを選択状態にします。
	止まる場合は、そのオブジェクトが所属するレイヤが表示されているか確認してください。

	@param obj_name: (str) [必須] 選択するオブジェクトの名前
	"""
	bpy.ops.object.select_all(action='DESELECT')
	bpy.data.objects[obj_name].hide = False
	bpy.data.objects[obj_name].select = True
	bpy.context.scene.objects.active = bpy.data.objects[obj_name]

	# 強制オブジェクトモード
	bpy.ops.object.mode_set(mode='OBJECT', toggle=False)

	print("%s を選択しました。" % obj_name)


def applyShapeAsBasis(obj_name: str, shape_name: Union[Sequence[str], str], blend: float = 1.0) -> bpy.types.Object:
	"""
	指定したモーフを基準状態として登録します。

	@param obj_name: (str) [必須] 編集するオブジェクトの名前
	@param shape_name: (str | [str]) [必須] 適用するシェイプキーの名前
	@param blend: (float) [任意] 元の状態に適用するシェイプキーをどのくらい混ぜるか
	@return: (bpy.types.Object) シェイプキーが適用されたオブジェクト
	"""
	selectThisObjOnly(obj_name)
	bpy.ops.object.duplicate_move() # 退避

	bpy.ops.object.mode_set(mode='EDIT')

	bpy.context.object.active_shape_key_index = 0 # ベース
	bpy.ops.mesh.select_all(action='SELECT')

	if type(shape_name) is str:
		if shape_name in bpy.context.active_object.data.shape_keys.key_blocks:
			bpy.ops.mesh.blend_from_shape(shape=shape_name, add=False, blend=blend)
			print("%s に %s を基準状態として登録しました。" % (obj_name, shape_name))
		else:
			print("警告: %s に %s というキーは存在しません。何も行いません。" % (obj_name, shape_name))
	else:
		for shp in shape_name:
			if shp in bpy.context.active_object.data.shape_keys.key_blocks:
				bpy.ops.mesh.blend_from_shape(shape=shp, add=False, blend=blend)
				bpy.ops.object.mode_set(mode='OBJECT')
				bpy.ops.object.mode_set(mode='EDIT')
				print("%s を基準状態として登録しました。" % shp)
			else:
				print("警告: %s に %s というキーは存在しません。何も行いません。" % (obj_name, shp))

	bpy.ops.object.mode_set(mode='OBJECT')

	return bpy.context.active_object


def changeBoneRoll(mode: bool) -> None:
	"""
	肩から末端方向へのボーンロールを変更します。
	廃止予定です。

	@param mode: (bool) [必須] `True`でロールを設定し、ローカル軸でのポージングを簡単にします。`False`でロールを初期化( 0 に)します。
	"""
	# 対象のボーン
	bones = ("肩", "腕", "腕捩", "ひじ", "手捩", "手首", "親指", "人指", "中指", "薬指", "小指")

	# アーマチュアを選ぶ
	selectThisObjOnly(selectArmature())
	bpy.ops.object.posemode_toggle()

	arm = bpy.data.objects[selectArmature()].data

	# ボーンを選ぶ
	for bone in bones:
		if "指" in bone:
			for num in ["０", "１", "２", "３"]:
				if arm.bones.find(bone + num + ".L") >= 0:
					arm.bones[bone + num + ".L"].select = True

				if arm.bones.find(bone + num + ".R") >= 0:
					arm.bones[bone + num + ".R"].select = True
		else:
			arm.bones[bone + ".L"].select = True
			arm.bones[bone + ".R"].select = True

	# 編集モードに入る
	bpy.ops.object.editmode_toggle()

	# オペレータ実行
	if mode:
		bpy.ops.armature.calculate_roll(type='GLOBAL_POS_Z')
	else:
		bpy.ops.armature.roll_clear()

	print("ボーンロールの切り替えが完了しました。")


def updateOldAction(action: str) -> None:
	"""
	GRiS1 を満たさない古いモーションを更新します。
	廃止予定です。

	@param action: (str) [必須] 更新するモーションの名前
	"""
	# 変数の準備
	# bones = ("肩", "腕", "腕捩", "ひじ", "手捩", "手首", "親指", "人指", "中指", "薬指", "小指")
	bones = ("腕")
	bone_list_ext = []
	bone_list_done = [] # 一度処理したボーンを再処理しないようにします。何もしないと四元数なので4回処理されてしまいます。

	# 非表示だと失敗します。
	bpy.data.objects[selectArmature()].hide = False

	# 処理するボーンの一覧をつくります。
	for bone in bones:
		if "指" in bone:
			for number in ("０", "１", "２", "３"):
				bone_list_ext.append(bone + number + ".L")
				bone_list_ext.append(bone + number + ".R")
		else:
			bone_list_ext.append(bone + ".L")
			bone_list_ext.append(bone + ".R")

	# ボーンごとにそれぞれ処理していきます。
	for bone in bone_list_ext:
		# ボーンの roll を取得します。
		bpy.ops.object.mode_set(mode='EDIT')
		try:
			rot = bpy.data.objects[selectArmature()].data.edit_bones[bone].roll
		except KeyError:
			bpy.ops.object.mode_set(mode='OBJECT')
			continue
		bpy.ops.object.mode_set(mode='OBJECT')

		# roll 分逆回転してキーフレームを打ち直します。
		for fcurve in bpy.data.actions[action].fcurves:
			if "[\"%s\"].rotation" % bone in fcurve.data_path and bone not in bone_list_done:
				print("%s を %f rad 修正しています..." % (fcurve.data_path, rot))

				for point in fcurve.keyframe_points:
					frame = point.co[0]

					bpy.context.scene.frame_set(frame)
					bpy.context.scene.update()
					print("Frame: %4d" % frame, end="\r")

					bpy.data.objects[selectArmature()].pose.bones[bone].rotation_quaternion.rotate(Euler((0, -rot, 0)))
					bpy.data.objects[selectArmature()].pose.bones[bone].keyframe_insert(data_path="rotation_quaternion")

				bone_list_done.append(bone)

	print("更新が終了しました。必ず結果が正しいか確認を行ってください。")


def toggleLegsIK(mode: bool) -> None:
	"""
	足 IK の有効/無効を切り替えます。

	@param mode: (bool) [必須] `True`で足 IK を有効に、`False`で無効にします。
	"""
	bones = ("ひざ.L", "ひざ.R", "足首.L", "足首.R")

	for bone in bones:
		bpy.data.objects[selectArmature()].pose.bones[bone].constraints["IK"].mute = not mode

	print("足IKの %s への切り替えが完了しました。" % mode)


def updatePmxComment(mmd_root: mmd_tools.properties.root.MMDRoot, identifier: Union[None, str] = None, mm_ver: Union[None, Sequence[int]] = None, copyright_jp: Union[None, str] = None, copyright_en: Union[None, str] = None, pname: Union[None, str] = None, additional_jp: Union[None, str] = None, additional_en: Union[None, str] = None) -> None:
	"""
	PMX ファイルに埋め込まれるメタデータを更新します。
	モジュールを呼び出した Blender ファイルと同じフォルダに`changelog`が存在している必要があります。

	@param mmd_root: (mmd_tools.properties.root.MMDRoot) [必須] モデルのルート
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


def switchLayers(enable: Sequence[int] = [0]) -> None:
	"""
	Switch scene layers.

	@param enable: [optional] ([int]) Layers enabled.
	"""
	layers = bpy.context.scene.layers

	for i in range(len(layers)):
		layers[i] = i in enable

	print("可視レイヤの切り替えが完了しました。")


def multiplyMass(mul: float, parent: str) -> None:
	"""
	物理演算の Blender-MMD 間のつじつまを合わせるために、剛体の質量に定数を乗じます。
	MMD は初期状態で Blender の10倍の重力加速度が設定されているようです。

	@param mul: (float) [必須] 質量の倍数
	@param parent: (str) [必須] 剛体の親。通常、`rigidbodies`です。
	"""
	for obj in bpy.data.objects[parent].children:
		obj.rigid_body.mass *= mul

	print("剛体の質量を %f 倍しました。" % mul)


def toggleSubsurf(mode: bool, target: Union[None, Sequence[bpy.types.Modifier]] = None, mod_type: Sequence[str] = ('SUBSURF')) -> Sequence[bpy.types.Modifier]:
	"""
	細分割曲面モディファイアおよび他のモディファイアの有効・無効を切り替えます。

	@param mode: (bool) [必須]
		有効にするか(`True`) 無効にするか(`False`)
	@param target: ([bpy.types.Modifier) [任意]
		対象とするモディファイアのリストです。指定した場合、`mod_type`は無視されます。
		未指定の場合、すべてのオブジェクトに設定された`mod_type`に該当するモディファイアを対象とします。
	@param mod_type: ((str)) [任意]
		切り替えるモディファイアのタイプ
	@return toggled: ([bpy.types.Modifier])
		切り替えたモディファイアのリスト
	"""
	toggled = []

	if target is None:
		for obj in bpy.data.objects:
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

	print("モディファイア %s を %s にしました。" % (toggled, mode))

	return toggled


def deleteVertexGroup(object_name: str, group_name: Sequence[str]) -> bpy.types.Object:
	"""
	指定されたオブジェクトの指定された頂点グループに属する頂点を削除します。
	軽量版の生成に用いられます。

	@param object_name (str): [必須] 対象とするオブジェクト
	@param group_name ([str]): [必須] 削除する頂点グループ名のリスト
	@return obj (bpy.types.Object): 指定の頂点が削除されたオブジェクト
	"""
	selectThisObjOnly(object_name)

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

	print("%s の %s に属する頂点を削除しました。" % (object_name, group_name))

	return obj


"""
Then what would you like to do?
Type "import quail" and quail.<function> in the console.
If you need help, type "help(quail)" in the console.
To reload this lib, type "import importlib; importlib.reload(quail)"
"""
